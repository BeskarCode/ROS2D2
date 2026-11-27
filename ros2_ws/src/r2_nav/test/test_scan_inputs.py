# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The lidar scan from the node's callback to the tick (NAV-3): kept as it arrives, turned into
points only when a fresh snapshot needs them, with the cos/sin table cached per geometry."""
import math
import random
from types import SimpleNamespace

import numpy as np
import pytest

from r2_nav import shaping
from r2_nav.shaping import SensorInputs, scan_points


def scan(n=360, value=None, seed=0):
    rng = random.Random(seed)
    r = [value if value is not None else rng.uniform(0.1, 10) for _ in range(n)]
    return SimpleNamespace(ranges=np.array(r, dtype=np.float32), angle_min=-math.pi,
                           angle_increment=2 * math.pi / n, range_min=0.05, range_max=12.0)


def old_points(m, x, y, yaw):
    pts = []
    for i, r in enumerate(m.ranges):
        if not math.isfinite(r) or r < m.range_min or r > m.range_max:
            continue
        a = m.angle_min + i * m.angle_increment + yaw
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    return pts


def test_lazy_snapshot_gives_the_old_points_and_ages():
    # REV-T3: on_scan_msg -> snapshot, against the old callback that made the points at once
    inputs = SensorInputs()
    m, pose = scan(seed=3), (0.2, -0.05, math.radians(10))
    inputs.on_scan_msg(1.0, m, pose)
    assert inputs.scan[1] is None                    # nothing worked out yet
    snap = inputs.snapshot(1.1, "lidar")
    assert np.allclose(snap.scan_xy, np.array(old_points(m, *pose)), atol=1e-9)
    assert snap.ages["lidar"] == pytest.approx(0.1)
    assert snap.lost == []


def test_a_stale_scan_is_not_converted_and_counts_as_lost_when_armed(monkeypatch):
    # REV-10: a scan too old to count is never turned into points
    called = []
    monkeypatch.setattr(shaping, "scan_points", lambda *a, **k: called.append(1) or np.empty((0, 2)))
    inputs = SensorInputs()
    inputs.arm(0.5)
    inputs.on_scan_msg(1.0, scan(), (0.0, 0.0, 0.0))
    snap = inputs.snapshot(1.0 + inputs.stale + 0.1, "lidar")
    assert snap.scan_xy is None and called == []
    assert snap.lost == ["lidar"]


def test_lidar_ignored_drops_the_scan():
    inputs = SensorInputs()
    inputs.on_scan_msg(1.0, scan(), (0.0, 0.0, 0.0))
    inputs.scan = None                               # what the nodes do with the lidar "ignored"
    assert inputs.snapshot(1.05, "lidar").scan_xy is None


def test_trig_table_reused_and_emptied_past_eight_geometries():
    # REV-T4
    shaping._TRIG.clear()
    m = scan()
    scan_points(m.ranges, m.angle_min, m.angle_increment, m.range_min, m.range_max)
    first = next(iter(shaping._TRIG.values()))
    scan_points(m.ranges, m.angle_min, m.angle_increment, m.range_min, m.range_max)
    assert len(shaping._TRIG) == 1 and next(iter(shaping._TRIG.values())) is first
    for yaw in range(1, 9):
        scan_points(m.ranges, m.angle_min, m.angle_increment, m.range_min, m.range_max, yaw=yaw * 0.1)
    assert len(shaping._TRIG) == 1                   # the ninth geometry empties it: only the newest is kept


def test_no_echo_and_out_of_range_rays_left_out():
    m = scan(n=4, value=1.0)
    m.ranges[:] = [np.inf, np.nan, 0.01, 20.0]
    assert scan_points(m.ranges, m.angle_min, m.angle_increment, m.range_min, m.range_max).shape == (0, 2)
