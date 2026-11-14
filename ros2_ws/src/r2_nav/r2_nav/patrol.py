# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Patrol: a route of points (odom, metres) gone round in a loop with the Go to a point logic.
A point it cannot reach (the navigator gives up) is skipped; when it reaches none in a row it
stops. No ROS here: test/test_patrol.py.

The route comes from the web page on /nav/patrol as JSON: [[x, y], [x, y], ...].
"""

import json
import math


def parse_route(text):
    """[(x, y), ...] from the JSON on /nav/patrol, or None when it is not a list of [x, y]."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, list):
        return None
    out = []
    for p in data:
        if not isinstance(p, list) or len(p) != 2:
            return None
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in p):
            return None
        out.append((float(p[0]), float(p[1])))
    return out


class Patrol:
    def __init__(self):
        self.points = []
        self.i = 0
        self.fails = 0          # points given up on in a row

    def set(self, points):
        self.points = list(points)
        self.i, self.fails = 0, 0

    def current(self):
        """The point it is heading for, or None (no route, or none reachable)."""
        if not self.points or self.fails >= len(self.points):
            return None
        return self.points[self.i]

    def after(self, state):
        """The navigator's state after a step: on "arrived" or "gave up", the next point."""
        if not self.points:
            return None
        if state == "arrived":
            self.fails = 0
        elif state == "gave up":
            self.fails += 1
        else:
            return self.current()
        self.i = (self.i + 1) % len(self.points)
        return self.current()
