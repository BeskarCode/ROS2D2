# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""REV-T7: the Mega bridge's serial reader against a pty (no Mega): one bad line does not kill it,
noise is thrown away, and a lost port is not opened again before reconnect_sec."""
import os
import pty
import threading
import time
import tty

import pytest
import rclpy

from r2_shadow_bridge.mega_bridge_node import MegaBridgeNode

MODES = os.path.join(os.path.dirname(__file__), "..", "..", "r2_nav", "config", "modes.yaml")


class Bench:
    def __init__(self, tmp_path):
        master, slave = pty.openpty()
        tty.setraw(slave)
        self.master, self.slave = master, slave
        self.port = tmp_path / "r2-mega"
        self.port.symlink_to(os.ttyname(slave))
        self.node = MegaBridgeNode(parameter_overrides=[
            rclpy.parameter.Parameter("port", value=str(self.port)),
            rclpy.parameter.Parameter("open_wait", value=0.0),
            rclpy.parameter.Parameter("reconnect_sec", value=0.5),
            rclpy.parameter.Parameter("modes_config", value=os.path.abspath(MODES)),
        ])
        self.rx = []
        self._stop = threading.Event()
        threading.Thread(target=self._drain, daemon=True).start()    # what the bridge sends: read and forget

    def _drain(self):
        while not self._stop.is_set():
            try:
                self.rx.append(os.read(self.master, 4096))
            except OSError:
                time.sleep(0.01)

    def send(self, data):
        os.write(self.master, data)

    def spin_until(self, cond, secs=5.0):
        end = time.monotonic() + secs
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.02)
            if cond():
                return True
        return False

    def close(self):
        self._stop.set()
        self.node._stop.set()
        self.node.destroy_node()
        for fd in (self.master, self.slave):
            try:
                os.close(fd)
            except OSError:
                pass


@pytest.fixture
def bench(tmp_path):
    rclpy.init()
    b = Bench(tmp_path)
    yield b
    b.close()
    rclpy.shutdown()


def test_one_bad_line_does_not_kill_the_reader(bench, monkeypatch):
    assert bench.spin_until(lambda: bench.node.ser is not None)
    seen = []
    real = bench.node._on_line

    def flaky(line):
        seen.append(line)
        if line == "BOOM":
            raise KeyError("boom")
        real(line)
    monkeypatch.setattr(bench.node, "_on_line", flaky)
    bench.send(b"BOOM\nAUTO OFF stick\n")
    assert bench.spin_until(lambda: "AUTO OFF stick" in seen)
    assert bench.node._reader.is_alive()


def test_noise_is_thrown_away_and_the_next_line_counts(bench, monkeypatch):
    assert bench.spin_until(lambda: bench.node.ser is not None)
    seen = []
    monkeypatch.setattr(bench.node, "_on_line", seen.append)
    bench.send(b"x" * 9000)
    bench.spin_until(lambda: False, 0.5)          # read (and thrown away) before the next line comes
    bench.send(b"\nTRACK OFF\n")
    assert bench.spin_until(lambda: "TRACK OFF" in seen)
    assert not any(len(s) > 8192 for s in seen)


def test_a_failed_write_waits_before_opening_again(bench):
    # REV-5: opening the port resets the Mega, so a stuck port must not be reopened in a loop
    assert bench.spin_until(lambda: bench.node.ser is not None)

    class Broken:
        in_waiting = 0

        def write(self, data):
            raise OSError("stuck")

        def read(self, n):
            time.sleep(0.01)
            return b""

        def close(self):
            pass
    with bench.node.lock:
        bench.node.ser = Broken()
    t0 = time.monotonic()
    assert bench.node._write("ROS:AUTO:?\n") is False
    assert bench.node.ser is None
    assert bench.spin_until(lambda: bench.node.ser is not None, 4)
    assert time.monotonic() - t0 >= 0.45
