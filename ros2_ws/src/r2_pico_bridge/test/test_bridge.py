# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The bridge node against a FakePico on a pty (no hardware): rclpy in the test process."""

import json
import math
import os
import pty
import time
import tty

import pytest
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Range
from std_msgs.msg import Bool, String

import r2_sensors.config
from r2_pico_bridge.fake_pico import FakePico
from r2_pico_bridge.pico_bridge_node import PicoBridge

PACKAGE_YAML = os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml")
NAMES = ["tof_front_left", "tof_front", "tof_front_right", "tof_floor",
         "sonar_front_left", "sonar_front_right", "sonar_rear", "sonar_left", "sonar_right"]


class Bench:
    """A FakePico behind a symlink (the node's port), the node, and a listener node."""

    def __init__(self, tmp_path, monkeypatch, proto=2):
        monkeypatch.setattr(r2_sensors.config, "USER_CONFIG", str(tmp_path / "none.yaml"))
        self.tmp = tmp_path
        self.config = tmp_path / "sensors.yaml"
        self.config.write_text(open(PACKAGE_YAML, encoding="utf-8").read(), encoding="utf-8")
        self.board = tmp_path / "pico_board.yaml"
        self.board.write_text("brightness: 2\n", encoding="utf-8")
        self.proto = proto
        self.port = tmp_path / "r2-pico"
        self.pico = None
        self.plug()
        self.node = PicoBridge(parameter_overrides=[
            rclpy.parameter.Parameter("port", value=str(self.port)),
            rclpy.parameter.Parameter("config", value=str(self.config)),
            rclpy.parameter.Parameter("reconnect_sec", value=0.2),
            rclpy.parameter.Parameter("stale_sec", value=1.0),
            rclpy.parameter.Parameter("telemetry_timeout_sec", value=1.0),
            rclpy.parameter.Parameter("board_config", value=str(self.board)),
        ])
        self.ear = rclpy.create_node("ear")
        self.state = None
        self.connected = None
        self.ranges = {}
        self.ear.create_subscription(String, "/pico/state", self._on_state, 10)
        self.ask_tm = self.ear.create_publisher(Bool, "/pico/telemetry_request", 10)
        self.cmd = self.ear.create_publisher(String, "/pico/command", 10)
        self.ear.create_subscription(
            Bool, "/pico/connected", lambda m: setattr(self, "connected", m.data),
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        for n in NAMES:
            self.ear.create_subscription(Range, f"/range/{n}", lambda m, n=n: self.ranges.setdefault(n, []).append(m),
                                         qos_profile_sensor_data)

    def _on_state(self, m):
        self.state = json.loads(m.data)

    def plug(self):
        master, slave = pty.openpty()
        tty.setraw(slave)
        if self.port.is_symlink():
            self.port.unlink()
        self.port.symlink_to(os.ttyname(slave))
        self.slave = slave
        self.pico = FakePico(master, hb_period=0.2, proto=self.proto)

    def unplug(self):
        self.pico.close()
        os.close(self.slave)

    def spin_until(self, cond, secs=5.0):
        end = time.monotonic() + secs
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.02)
            rclpy.spin_once(self.ear, timeout_sec=0.02)
            if cond():
                return True
        return False

    def close(self):
        self.node.destroy_node()
        self.ear.destroy_node()
        self.unplug()


@pytest.fixture
def bench(tmp_path, monkeypatch):
    rclpy.init()
    b = Bench(tmp_path, monkeypatch)
    yield b
    b.close()
    rclpy.shutdown()


def sensors(b):
    return (b.state or {}).get("sensors", {})


def test_on_connect_it_says_hello_and_sends_the_sensors(bench):
    assert bench.spin_until(lambda: bench.pico.cfg_lines)
    assert bench.pico.cfg_lines[0] == "CFG V:2 V:3 V:4 V:5 S:10:11 S:12:13 S:14:15 S:18:19 S:20:21"
    assert bench.spin_until(lambda: bench.connected is True)
    assert bench.spin_until(lambda: sensors(bench) == {n: "not_responding" for n in NAMES})
    assert bench.state["connected"] is True and bench.state["firmware"] == "0.2.0"
    assert bench.state["config_error"] is None
    bench.spin_until(lambda: False, 0.5)
    assert bench.ranges == {}


def test_a_sensor_that_answers_publishes_its_range(bench):
    bench.pico.states = "ONNNNNN"
    bench.pico.readings = {0: 420}
    assert bench.spin_until(lambda: bench.ranges.get("tof_front_left"))
    m = bench.ranges["tof_front_left"][-1]
    assert m.range == pytest.approx(0.42)
    assert m.radiation_type == Range.INFRARED
    assert m.header.frame_id == "tof_front_left_link"
    assert m.max_range == pytest.approx(1.2)
    assert m.field_of_view == pytest.approx(math.radians(25))
    assert sensors(bench)["tof_front_left"] == "ok"


def test_nothing_in_range_is_infinity(bench):
    bench.pico.states = "NNNNONN"
    bench.pico.readings = {4: -1}
    assert bench.spin_until(lambda: bench.ranges.get("sonar_front_left"))
    m = bench.ranges["sonar_front_left"][-1]
    assert math.isinf(m.range) and m.radiation_type == Range.ULTRASOUND


def test_a_sensor_that_stops_answering_stops_publishing(bench):
    bench.pico.states = "ONNNNNN"
    bench.pico.readings = {0: 420}
    assert bench.spin_until(lambda: bench.ranges.get("tof_front_left"))
    bench.pico.states = "NNNNNNN"
    assert bench.spin_until(lambda: sensors(bench).get("tof_front_left") == "not_responding")
    # let readings published before the 'N' arrive first, so they are not counted below
    bench.spin_until(lambda: False, 0.3)
    # an R that was already on its way must not be published once the sensor is 'N'
    bench.node.on_line("R 0:300")
    count = len(bench.ranges["tof_front_left"])
    bench.spin_until(lambda: False, 0.5)
    assert len(bench.ranges["tof_front_left"]) == count


def test_a_pico_without_sensors_gets_them_again(bench):
    assert bench.spin_until(lambda: bench.pico.cfg_lines)
    bench.pico.n = None             # as if it had restarted
    assert bench.spin_until(lambda: len(bench.pico.cfg_lines) >= 2)


def test_unplug_and_plug_again(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    bench.unplug()
    assert bench.spin_until(lambda: bench.connected is False, 4)
    assert bench.spin_until(lambda: bench.state and bench.state["connected"] is False)
    bench.plug()
    assert bench.spin_until(lambda: bench.pico.cfg_lines, 4)
    assert bench.spin_until(lambda: bench.connected is True)


def test_saving_sensors_yaml_sends_the_new_sensors(bench):
    assert bench.spin_until(lambda: bench.pico.cfg_lines)
    text = bench.config.read_text(encoding="utf-8")
    start = text.index("sonar_rear:")
    bench.config.write_text(text[:start], encoding="utf-8")
    t = os.path.getmtime(bench.config) + 5
    os.utime(bench.config, (t, t))
    assert bench.spin_until(lambda: bench.pico.cfg_lines[-1] == "CFG V:2 V:3 V:4 V:5 S:10:11 S:12:13", 4)
    assert bench.spin_until(lambda: "sonar_rear" not in sensors(bench))


def test_a_broken_sensors_yaml_keeps_the_last_good_one(bench):
    assert bench.spin_until(lambda: sensors(bench) == {n: "not_responding" for n in NAMES})
    sent = len(bench.pico.cfg_lines)
    bench.config.write_text("tof_front: [1", encoding="utf-8")
    t = os.path.getmtime(bench.config) + 5
    os.utime(bench.config, (t, t))
    bench.spin_until(lambda: False, 1.5)
    assert len(bench.pico.cfg_lines) == sent
    assert sensors(bench) == {n: "not_responding" for n in NAMES}


def test_a_refused_cfg_is_shown(bench):
    bench.unplug()
    bench.plug()
    bench.pico.cfg_error = "pin 16 reserved"     # before the node reconnects (reconnect_sec 0.2)
    assert bench.spin_until(lambda: bench.state and bench.state.get("config_error") == "pin 16 reserved", 4)


def test_a_glitched_negative_reading_is_never_infinity(bench):
    bench.pico.states = "ONNNNNN"
    assert bench.spin_until(lambda: sensors(bench).get("tof_front_left") == "ok")
    bench.node.on_line("R 0:-5")
    bench.spin_until(lambda: False, 0.3)
    assert not any(math.isinf(m.range) for m in bench.ranges.get("tof_front_left", []))


def test_closer_than_range_min_is_range_min(bench):
    bench.pico.states = "ONNNNNN"
    bench.pico.readings = {0: 10}          # something touching the ToF: 1 cm, under its 3 cm minimum
    assert bench.spin_until(lambda: bench.ranges.get("tof_front_left"))
    assert bench.ranges["tof_front_left"][-1].range == pytest.approx(0.03)


def test_no_pico_sensors_is_still_connected(bench):
    lidar_only = "lidar:\n  type: rplidar_c1\n  port: /dev/r2-lidar\n  x: 0.17\n  y: 0\n  z: 0.11\n"
    bench.config.write_text(lidar_only, encoding="utf-8")
    t = os.path.getmtime(bench.config) + 5
    os.utime(bench.config, (t, t))
    assert bench.spin_until(lambda: bench.pico.cfg_lines and bench.pico.cfg_lines[-1] == "CFG", 4)
    bench.spin_until(lambda: False, 2.0)        # longer than stale_sec
    assert bench.connected is True and bench.state["connected"] is True


def test_state_has_commit_and_proto(bench):
    assert bench.spin_until(lambda: bench.state and bench.state.get("commit") == "fake123")
    assert bench.state["firmware"] == "0.2.0" and bench.state["proto"] == 2


def test_telemetry_on_request_and_off_after_the_timeout(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    assert bench.state.get("telemetry") is None
    assert "TM 1" not in bench.pico.lines                    # nothing until asked

    def asking():
        bench.ask_tm.publish(Bool(data=True))
        return bench.state and bench.state.get("telemetry")
    assert bench.spin_until(asking)
    assert bench.pico.lines.count("TM 1") == 1               # asked once, not on every request
    assert bench.state["telemetry"]["rps"] == [20, 20]
    # the console goes away: no more requests -> off within the timeout (1 s here)
    assert bench.spin_until(lambda: "TM 0" in bench.pico.lines, 3)
    assert bench.spin_until(lambda: bench.state.get("telemetry") is None, 3)


def test_telemetry_false_turns_it_off_at_once(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    assert bench.spin_until(lambda: (bench.ask_tm.publish(Bool(data=True)), "TM 1" in bench.pico.lines)[1])
    bench.ask_tm.publish(Bool(data=False))
    assert bench.spin_until(lambda: "TM 0" in bench.pico.lines, 0.5)


def test_telemetry_resent_after_reconnect(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    assert bench.spin_until(lambda: (bench.ask_tm.publish(Bool(data=True)), "TM 1" in bench.pico.lines)[1])
    bench.unplug()
    assert bench.spin_until(lambda: (bench.ask_tm.publish(Bool(data=True)), bench.connected is False)[1], 4)
    bench.plug()
    assert bench.spin_until(lambda: (bench.ask_tm.publish(Bool(data=True)), "TM 1" in bench.pico.lines)[1], 4)


def touch_later(path):
    t = os.path.getmtime(path) + 5
    os.utime(path, (t, t))


def test_ui_sent_after_cfg_and_on_file_change(bench):
    assert bench.spin_until(lambda: "UI t=30 b=2 led=auto" in bench.pico.lines)
    lines = bench.pico.lines
    assert lines.index("UI t=30 b=2 led=auto") > max(i for i, l in enumerate(lines) if l.startswith("CFG"))
    bench.board.write_text("display_timeout_s: 0\nleds: errors\n", encoding="utf-8")
    touch_later(bench.board)
    assert bench.spin_until(lambda: "UI t=0 b=2 led=err" in bench.pico.lines, 4)
    assert bench.spin_until(lambda: bench.state.get("settings_supported") is True)


def test_a_broken_board_file_keeps_the_last_good_settings(bench):
    assert bench.spin_until(lambda: "UI t=30 b=2 led=auto" in bench.pico.lines)
    n = len([l for l in bench.pico.lines if l.startswith("UI")])
    bench.board.write_text("brightness: 9\n", encoding="utf-8")
    touch_later(bench.board)
    bench.spin_until(lambda: False, 2.5)
    assert len([l for l in bench.pico.lines if l.startswith("UI")]) == n


def test_ui_resent_after_reconnect(bench):
    assert bench.spin_until(lambda: "UI t=30 b=2 led=auto" in bench.pico.lines)
    bench.unplug()
    assert bench.spin_until(lambda: bench.connected is False, 4)
    bench.plug()
    assert bench.spin_until(lambda: "UI t=30 b=2 led=auto" in bench.pico.lines, 4)


def test_command_only_disp_and_id(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    for c in ("ID US3", "DISP on VL2", "BOOT", "TM 1", "DISP on\nBOOT"):
        bench.cmd.publish(String(data=c))
    assert bench.spin_until(lambda: "DISP on VL2" in bench.pico.lines)
    bench.spin_until(lambda: False, 0.3)
    assert "ID US3" in bench.pico.lines
    assert "BOOT" not in bench.pico.lines and "TM 1" not in bench.pico.lines


def test_old_firmware_marks_settings_unsupported(tmp_path, monkeypatch):
    rclpy.init()
    old = Bench.__new__(Bench)
    try:
        Bench.__init__(old, tmp_path, monkeypatch, proto=1)
        assert old.spin_until(lambda: old.state and old.state.get("settings_supported") is False)
        n = len([l for l in old.pico.lines if l.startswith("UI")])
        old.spin_until(lambda: False, 1.5)
        assert len([l for l in old.pico.lines if l.startswith("UI")]) == n     # not hammered
    finally:
        old.close()
        rclpy.shutdown()


def release(bench, on):
    from std_srvs.srv import SetBool
    client = bench.ear.create_client(SetBool, "/pico/release")
    assert client.wait_for_service(timeout_sec=2.0)
    fut = client.call_async(SetBool.Request(data=on))
    assert bench.spin_until(lambda: fut.done())
    return fut.result()


def test_release_sends_boot_and_keeps_port_closed(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    assert release(bench, True).success
    assert bench.spin_until(lambda: "BOOT" in bench.pico.lines)
    assert bench.spin_until(lambda: bench.connected is False, 4)
    hellos = bench.pico.lines.count("HELLO")
    bench.spin_until(lambda: False, 1.5)                    # reconnect_sec is 0.2: it would have
    assert bench.pico.lines.count("HELLO") == hellos        # opened it again by now


def test_release_false_reconnects_and_resends_everything(bench):
    assert bench.spin_until(lambda: bench.connected is True)
    assert release(bench, True).success
    assert bench.spin_until(lambda: bench.connected is False, 4)
    bench.unplug()                      # the Pico restarts with the new firmware...
    bench.plug()                        # ...and comes back as a new serial device
    assert release(bench, False).success
    assert bench.spin_until(lambda: bench.pico.cfg_lines and "UI t=30 b=2 led=auto" in bench.pico.lines, 4)
    assert bench.spin_until(lambda: bench.connected is True)


def test_state_says_what_the_display_shows(bench):
    assert bench.spin_until(lambda: bench.state and bench.state.get("display") == "off")
    bench.cmd.publish(String(data="DISP on US2"))
    assert bench.spin_until(lambda: bench.state.get("display") == "US2")
