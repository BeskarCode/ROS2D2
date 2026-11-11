# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Text protocol of the Pico that reads the distance sensors (firmware/r2_pico_sensors).

USB serial, one ASCII line each.

Pi -> Pico:
  HELLO                       answers PICO r2_pico_sensors <fw> proto 2 commit <git commit>
                              (proto 1 firmware: no commit)
  CFG V:<xshut> S:<trig>:<echo> ...
                              the sensors, in order (a sensor's index is its place);
                              answers CFG OK <n> or CFG ERR <why>
  BOOT                        restart into the USB loader (to flash it)
  TM 1 / TM 0                 telemetry on / off (answers TM OK; off after a restart)

Pico -> Pi:
  HB <ms> <states>            every second; states '-' = no CFG yet, else one letter per
                              sensor: O answers, N not answering
  R <i>:<mm> <i>:<mm> ...     every 50 ms, new readings; mm -1 = answers, nothing in range
  T c0=% c1=% bus=% disp=% wait=<ms> temp=<tenths °C> up=<s> rps=<n>,<n>,...
                              with TM 1, every second: each core's load, the I2C bus held (and
                              by the display), the longest a VL53L0X waited for it, the chip's
                              temperature, seconds up, readings per second of each sensor
  ERR <text>                  a line it did not understand
"""

import re

from r2_sensors.config import PICO_PINS

PROTO = 2
_HB = re.compile(r"^HB (\d+)(?: (-|[ON]*))?$")    # no states: CFG with no sensors
_R_ITEM = re.compile(r"^(\d+):(-?\d+)$")
_HELLO = re.compile(r"^PICO r2_pico_sensors (\S+) proto (\d+)(?: commit (\S+))?$")
_TM = re.compile(r"^T c0=(\d+) c1=(\d+) bus=(\d+) disp=(\d+) wait=(\d+) temp=(-?\d+) up=(\d+) rps=((?:\d+(?:,\d+)*)?)$")


def cfg_line(sensors):
    """("CFG V:2 S:10:11\\n", [names in the same order]) for the Pico's sensors, in file order."""
    items, names = [], []
    for name, s in sensors.items():
        if s.get("type") not in PICO_PINS:
            continue
        pins = [str(s["pico"][k]) for k in PICO_PINS[s["type"]]]
        items.append(("V:" if s["type"] == "vl53l0x" else "S:") + ":".join(pins))
        names.append(name)
    return "CFG" + "".join(" " + i for i in items) + "\n", names


def parse(line):
    """One line from the Pico as a tuple, or None if it is not one of the protocol's."""
    m = _HB.match(line)
    if m:
        return ("hb", int(m.group(1)), None if m.group(2) == "-" else m.group(2) or "")
    if line.startswith("R "):
        out = []
        for item in line[2:].split():
            m = _R_ITEM.match(item)
            if not m:
                return None
            out.append((int(m.group(1)), int(m.group(2))))
        return ("r", out) if out else None
    m = _HELLO.match(line)
    if m:
        return ("hello", m.group(1), int(m.group(2)), m.group(3))
    if line == "TM OK":
        return ("tm_ok",)
    m = _TM.match(line)
    if m:
        g = m.groups()
        return ("tm", {"c0": int(g[0]), "c1": int(g[1]), "bus": int(g[2]), "disp": int(g[3]),
                       "wait_ms": int(g[4]), "temp_c": int(g[5]) / 10, "up_s": int(g[6]),
                       "rps": [int(x) for x in g[7].split(",")] if g[7] else []})
    m = re.match(r"^CFG OK (\d+)$", line)
    if m:
        return ("cfg_ok", int(m.group(1)))
    if line.startswith("CFG ERR "):
        return ("cfg_err", line[8:])
    if line.startswith("ERR "):
        return ("err", line[4:])
    return None
