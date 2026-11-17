# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Between the topics and the navigation logic, and between the logic and the feet, without ROS.
The navigator node, the follow node and the closed-loop tests use the same code.

SensorInputs keeps the last reading of each sensor, filtered as it arrives (not at the 10 Hz
tick), says how old each one is, and which went silent after reporting: a sensor that stops
reporting is a sensor lost, never "nothing there".

shape() turns what the logic wants into what goes to the feet: up with `accel`, down with `decel`,
and a hard stop cuts the forward speed at once (no ramp down when something is in the way).
"""
import math

from r2_nav.nav_core import RangeFilter, ramp

STALE = 0.5          # s: a sensor older than this is not reporting


class Snapshot:
    def __init__(self, scan_xy, ranges, raw, lost, ages):
        self.scan_xy = scan_xy      # lidar points in base_link, or None when the lidar is silent
        self.ranges = ranges        # {name: metres | None} of the distance sensors reporting (filtered)
        self.raw = raw              # the same, unfiltered
        self.lost = lost            # names that reported and went silent (the lidar: since the mode started)
        self.ages = ages            # {name: s since its last reading}


class SensorInputs:
    def __init__(self, stale=STALE):
        self.stale = stale
        self.ranges = {}            # name -> (time, raw, filtered)
        self.filters = {}
        self.scan = None            # (time, points)
        self.armed = None           # when the current mode started (the lidar may only spin from then on)

    def arm(self, now):
        self.armed = now

    def disarm(self):
        self.armed = None

    def on_range(self, name, now, reading, use_filter=True):
        """reading: metres, or None when the sensor sees nothing."""
        f = self.filters.setdefault(name, RangeFilter())
        prev = self.ranges.get(name)
        if prev is not None and now - prev[0] >= self.stale:
            f.reset()                               # back after a silence: no old history mixed in
        self.ranges[name] = (now, reading, f.update(reading) if use_filter else reading)

    def on_scan(self, now, points):
        self.scan = (now, points)

    def forget(self, name):
        """An ignored sensor: as if it had never reported."""
        self.ranges.pop(name, None)
        self.filters.pop(name, None)

    def snapshot(self, now, lidar_name=None):
        scan_xy = self.scan[1] if self.scan and now - self.scan[0] < self.stale else None
        ranges, raw, ages, lost = {}, {}, {}, []
        for name, (t, r, val) in self.ranges.items():
            ages[name] = now - t
            if now - t >= self.stale:
                lost.append(name)                   # it reported, then went silent
                self.filters.get(name, RangeFilter()).reset()
                continue
            raw[name], ranges[name] = r, val
        if lidar_name and self.scan:
            ages[lidar_name] = now - self.scan[0]
            if scan_xy is None and self.armed is not None and self.scan[0] >= self.armed:
                lost.append(lidar_name)
        return Snapshot(scan_xy, ranges, raw, sorted(lost), ages)


def shape(out, want_v, want_w, hard_stop, cfg, dt):
    """(v, w) for the feet from the last (v, w) and what the logic wants."""
    v, w = out
    speeding_up = abs(want_v) > abs(v) and want_v * v >= 0
    v = ramp(v, want_v, (cfg["accel"] if speeding_up else cfg["decel"]) * dt)
    w = ramp(w, want_w, math.radians(cfg["turn_accel_deg"]) * dt)
    if hard_stop and want_v <= 0:
        v = min(v, 0.0)                             # a stop is a stop: forward speed cut at once (turning keeps its ramp)
    if not cfg["allow_reverse"]:
        v = max(0.0, v)
    return v, w
