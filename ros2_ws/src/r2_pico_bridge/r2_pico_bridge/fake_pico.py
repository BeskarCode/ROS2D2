# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""A pretend Pico (firmware/r2_pico_sensors) on the master side of a pty, for tests and the
bench: it answers HELLO and CFG, sends HB and R lines like the real one.

    python3 -m r2_pico_bridge.fake_pico            # makes a pty and prints its path

The sensors' answers are set from the outside: .states ('O'/'N' per sensor; missing ones
are 'N') and .readings ({index: mm}, sent in every R line for the 'O' sensors).
"""

import os
import select
import sys
import threading
import time


class FakePico:
    def __init__(self, fd, hb_period=1.0, r_period=0.05):
        self.fd = fd
        self.hb_period = hb_period
        self.r_period = r_period
        self.cfg_lines = []         # every CFG received, as sent
        self.n = None               # sensors of the last good CFG; None = none yet
        self.states = ""
        self.readings = {}
        self.cfg_error = None       # set it to answer CFG ERR <this>
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)
        try:
            os.close(self.fd)
        except OSError:
            pass

    def _send(self, line):
        try:
            os.write(self.fd, (line + "\n").encode())
        except OSError:
            self._stop.set()

    def _on(self, line):
        if line == "HELLO":
            self._send("PICO r2_pico_sensors 0.1.0 proto 1")
        elif line == "CFG" or line.startswith("CFG "):
            self.cfg_lines.append(line)
            if self.cfg_error:
                self.n = None
                self._send(f"CFG ERR {self.cfg_error}")
            else:
                self.n = len(line.split()) - 1
                self._send(f"CFG OK {self.n}")
        elif line:
            self._send("ERR unknown")

    def _state(self, i):
        return self.states[i] if i < len(self.states) else "N"

    def _run(self):
        buf = b""
        t0 = time.monotonic()
        next_hb = next_r = t0
        while not self._stop.is_set():
            r, _, _ = select.select([self.fd], [], [], 0.01)
            if r:
                try:
                    data = os.read(self.fd, 256)
                except OSError:
                    return
                buf += data
                *lines, buf = buf.replace(b"\r", b"").split(b"\n")
                for line in lines:
                    self._on(line.decode(errors="replace").strip())
            now = time.monotonic()
            if now >= next_hb:
                next_hb = now + self.hb_period
                states = "-" if self.n is None else "".join(self._state(i) for i in range(self.n))
                self._send(f"HB {int((now - t0) * 1000)} {states}")
            if now >= next_r and self.n:
                next_r = now + self.r_period
                items = [f"{i}:{mm}" for i, mm in sorted(self.readings.items())
                         if i < self.n and self._state(i) == "O"]
                if items:
                    self._send("R " + " ".join(items))


def main():
    import pty
    import tty
    master, slave = pty.openpty()
    tty.setraw(slave)
    print(os.ttyname(slave), flush=True)
    pico = FakePico(master)
    pico.states = "O" * 12
    pico.readings = {i: 400 + 100 * i for i in range(12)}
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pico.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
