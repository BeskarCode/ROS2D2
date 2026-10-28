# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math

import pytest

from r2_sensors.scan import crop, fake_ranges


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
