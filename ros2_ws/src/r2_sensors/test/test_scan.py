# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math

import pytest

from r2_sensors.scan import blanked, crop, fake_ranges, mask


def test_crop_keeps_the_rays_the_droid_does_not_hide():
    n = 361
    angle_min, inc = -math.pi, 2 * math.pi / (n - 1)
    out = crop([1.0] * n, angle_min, inc, -math.radians(100), math.radians(100))
    for i, r in enumerate(out):
        a = angle_min + i * inc
        if abs(a) <= math.radians(100) - 1e-9:
            assert r == 1.0
        elif abs(a) > math.radians(100) + 1e-9:
            assert r == math.inf


def test_fake_room_ahead_and_behind():
    assert fake_ranges((0.17, 0.0), 0.0, [0.0], 12.0)[0] == pytest.approx(1.83)
    assert fake_ranges((0.17, 0.0), 0.0, [math.pi], 12.0)[0] == pytest.approx(1.67)


def test_fake_room_beyond_range_is_inf():
    assert fake_ranges((0.17, 0.0), 0.0, [0.0], 1.0)[0] == math.inf


def test_fake_room_sees_the_chair_leg():
    a = math.atan2(0.3, 0.63)
    assert fake_ranges((0.17, 0.0), 0.0, [a], 12.0)[0] == pytest.approx(math.hypot(0.63, 0.3) - 0.02, abs=1e-3)


def test_fake_room_turns_with_the_lidar():
    # lidar turned 90 deg left: its ray 0 hits the left wall (y = +1.5)
    assert fake_ranges((0.0, 0.0), math.pi / 2, [0.0], 12.0)[0] == pytest.approx(1.5)


def test_mask_drops_only_the_sector():
    from r2_sensors.scan import mask
    r = mask([1.0] * 360, -math.pi, math.radians(1), [(math.radians(10), math.radians(20))])
    assert sum(math.isinf(x) for x in r) == 11 and math.isinf(r[190]) and not math.isinf(r[201])


def test_mask_wraps_180():
    from r2_sensors.scan import mask
    r = mask([1.0] * 360, -math.pi, math.radians(1), [(math.radians(170), math.radians(-170))])
    assert math.isinf(r[0]) and math.isinf(r[355]) and not math.isinf(r[180])


def _old_crop_mask(ranges, amin, inc, lower, upper, sectors):
    out = []
    for i, r in enumerate(ranges):
        a = amin + i * inc
        out.append(r if lower - 1e-9 <= a <= upper + 1e-9 else math.inf)
    return mask(out, amin, inc, sectors) if sectors else out


def test_blanked_indices_match_crop_and_mask():
    # NAV-4: the cached indices written in place give the same scan as crop + mask
    import random
    rng = random.Random(4)
    for _ in range(50):
        n = rng.choice([360, 455, 720])
        amin = -math.pi
        inc = 2 * math.pi / n
        half = math.radians(rng.uniform(60, 360) / 2)
        sectors = [(math.radians(rng.uniform(-180, 180)), math.radians(rng.uniform(-180, 180)))
                   for _ in range(rng.randint(0, 2))]
        ranges = [rng.uniform(0.1, 10) for _ in range(n)]
        want = _old_crop_mask(ranges, amin, inc, -half, half, sectors)
        got = list(ranges)
        for i in blanked(n, amin, inc, -half, half, sectors):
            got[i] = math.inf
        assert got == want


def test_crop_of_a_scan_from_0_to_2pi():
    # a driver that gives 0..2pi: the rays just right of the front (near 2pi) are kept too
    n = 360
    inc = 2 * math.pi / n
    out = crop([1.0] * n, 0.0, inc, -math.pi / 2, math.pi / 2)
    kept = [i for i, r in enumerate(out) if r == 1.0]
    assert 0 in kept and 89 in kept and 359 in kept and 271 in kept
    assert 180 not in kept and 135 not in kept


def test_blanked_on_a_scan_from_0_to_2pi():
    # REV-T2: the node's path (blanked) with angle_min = 0, as a driver giving 0..2pi would
    n = 360
    inc = 2 * math.pi / n
    half = math.radians(100)
    sectors = [(math.radians(170), math.radians(-170))]          # a blind sector across the back
    idx = set(blanked(n, 0.0, inc, -half, half, sectors))
    kept = [i for i in range(n) if i not in idx]
    assert 0 in kept and 99 in kept and 359 in kept and 261 in kept    # both sides of the front kept
    assert 101 not in kept and 180 not in kept and 259 not in kept     # the back blanked
    want = [i for i, r in enumerate(mask(crop([1.0] * n, 0.0, inc, -half, half), 0.0, inc, sectors)) if r != 1.0]
    assert sorted(idx) == want
