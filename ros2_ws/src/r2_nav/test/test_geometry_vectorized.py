# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""NAV-2 / NAV-3: the navigator's geometry with numpy gives what the plain Python one gave (the
same heading, the same free distance, the same nearest point) on random scans. The old code is
kept here as the reference: this is safety logic."""
import math
import random

import numpy as np
import pytest

from r2_nav.nav_core import HALF_WIDTH, INSIDE_MARGIN, choose_heading, clearance, inside_ahead, nearest_ahead, wrap
from r2_nav.shaping import scan_points


# ---- the reference: the code before NAV-2 / NAV-3, as it was
def old_nearest_ahead(points):
    return min((math.hypot(x, y) for x, y in points if x > 0), default=3.0)


def old_clearance(points, heading, half_width=HALF_WIDTH):
    c, s = math.cos(heading), math.sin(heading)
    best = 3.0
    for x, y in points:
        along, side = x * c + y * s, abs(-x * s + y * c)
        if along > 0 and side < half_width:
            best = min(best, along)
    return best


def old_inside_ahead(points, radius, cone_deg=60):
    best = None
    for x, y in points:
        d = math.hypot(x, y)
        if x > 0 and abs(math.atan2(y, x)) <= math.radians(cone_deg) and d < radius - INSIDE_MARGIN and (best is None or d < best[2]):
            best = (x, y, d)
    return best


def old_choose_heading(points, goal_bearing, cfg, allowed=None):
    margin = cfg["safety_radius"] + cfg["slow_from"]
    best = None
    for o in range(-90, 91, 10):
        h = math.radians(o)
        if allowed is not None and not allowed(h):
            continue
        c = old_clearance(points, h)
        cost = abs(wrap(h - goal_bearing)) / math.pi + (max(0.0, margin - c) * 2.5) + abs(o) / 900
        if best is None or cost < best[2]:
            best = (h, c, cost)
    return (0.0, 0.0) if best is None else (best[0], best[1])


def old_scan_xy(ranges, amin, inc, rmin, rmax, lx, ly, yaw):
    pts = []
    for i, r in enumerate(ranges):
        if not math.isfinite(r) or r < rmin or r > rmax:
            continue
        a = amin + i * inc + yaw
        pts.append((lx + r * math.cos(a), ly + r * math.sin(a)))
    return pts


CFG = {"safety_radius": 0.55, "slow_from": 0.6}


def random_scan(rng, n=455):
    ranges = []
    for _ in range(n):
        k = rng.random()
        ranges.append(math.inf if k < 0.15 else math.nan if k < 0.18 else rng.uniform(0.02, 14.0))
    return ranges


@pytest.mark.parametrize("seed", range(40))
def test_same_decisions_as_the_plain_python_geometry(seed):
    rng = random.Random(seed)
    ranges = [float(r) for r in np.array(random_scan(rng), dtype=np.float32)]    # a LaserScan holds float32
    n = len(ranges)
    geom = (-math.pi, 2 * math.pi / n, 0.05, 12.0, rng.uniform(0, 0.3), rng.uniform(-0.1, 0.1), rng.uniform(-0.3, 0.3))
    old = old_scan_xy(ranges, *geom)
    new = scan_points(np.array(ranges, dtype=np.float32), *geom)
    assert new.shape == (len(old), 2)
    assert np.allclose(new, np.array(old).reshape(-1, 2), atol=1e-12)
    pts = [tuple(p) for p in new]            # the same points for both, so the decisions must match
    assert nearest_ahead(new) == pytest.approx(old_nearest_ahead(pts), abs=1e-12)
    for h in (0.0, math.radians(60), -math.radians(60), math.pi, rng.uniform(-math.pi, math.pi)):
        assert clearance(new, h) == pytest.approx(old_clearance(pts, h), abs=1e-12)
    for radius in (0.3, 0.8, 1.5):
        o, v = old_inside_ahead(pts, radius, 50), inside_ahead(new, radius, 50)
        assert (o is None) == (v is None)
        if o:
            assert v == pytest.approx(o, abs=1e-12)
    goal = rng.uniform(-math.pi, math.pi)
    lim = math.radians(rng.choice([40, 95]))
    allowed = (lambda h: abs(h) < lim) if seed % 2 else None
    assert choose_heading(new, goal, CFG, allowed) == pytest.approx(old_choose_heading(pts, goal, CFG, allowed), abs=1e-12)
    assert choose_heading(pts, goal, CFG, allowed) == choose_heading(new, goal, CFG, allowed)   # a list works too


def test_no_points_at_all():
    assert nearest_ahead([]) == 3.0
    assert clearance([], 0.3) == 3.0
    assert inside_ahead(np.empty((0, 2)), 1.0) is None
    assert choose_heading([], 0.0, CFG) == old_choose_heading([], 0.0, CFG)
    assert choose_heading([], 0.0, CFG, allowed=lambda h: False) == (0.0, 0.0)
