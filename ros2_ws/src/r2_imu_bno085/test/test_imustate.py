# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Counters, /imu/status and the simulated IMU (pure, no ROS)."""

import json

import pytest

from r2_imu_bno085.calib import DEFAULTS
from r2_imu_bno085.imustate import Stats, sim_sample, status


def test_fps_counts_the_last_second():
    s = Stats()
    for i in range(150):
        s.frame(i / 100, 0, 0, (0, 0, 9.80665))
    assert s.fps(1.49) == 100


def test_fps_is_zero_without_frames():
    assert Stats().fps(5.0) == 0


def test_bump_is_the_peak_without_gravity():
    s = Stats()
    s.frame(0.0, 0, 0, (0, 0, 9.80665))
    s.frame(0.5, 0, 0, (7.0, 0, 9.80665))
    assert s.bump(0.6) == pytest.approx(7.0) and s.bump(2.0) == 0.0


def test_last_second_keeps_raw_angles():
    s = Stats()
    for i in range(200):
        s.raw(i / 100, 179.0, 2.0)
    last = s.last_second(1.99)
    assert len(last) == 100 and last[0] == (179.0, 2.0)


def test_status_json():
    d = json.loads(status(connected=True, port="/dev/ttyAMA3", fps=100, bad_frames=0, cfg=DEFAULTS,
                          last_frame_age=0.01, bump=0.333, simulate=False, error=""))
    assert d["levelled"] is False and d["bump"] == 0.33 and d["box"] == "standing" and d["fps"] == 100
    assert set(d) == {"connected", "port", "fps", "bad_frames", "levelled", "level", "box", "front", "in_use",
                      "invert_yaw", "last_frame_age", "bump", "simulate", "error"}


def test_status_levelled_and_no_frame_yet():
    cfg = dict(DEFAULTS, level={"roll_deg": 179.0, "pitch_deg": 2.0})
    d = json.loads(status(connected=False, port="/dev/ttyAMA3", fps=0, bad_frames=3, cfg=cfg,
                          last_frame_age=None, bump=0.0, simulate=False, error=""))
    assert d["levelled"] is True and d["last_frame_age"] is None and d["level"]["roll_deg"] == 179.0


def test_sim_sample_is_still_on_average():
    s = sim_sample(0.0, 0)
    assert (s.roll, s.pitch, s.yaw) == pytest.approx((0, 0, 0))
    assert s.accel[2] == pytest.approx(9.80665, abs=0.4) and s.index == 0


def test_sim_sample_yaw_wraps():
    assert -180.0 <= sim_sample(20.0, 2000).yaw < 180.0 and sim_sample(20.0, 2000).index == 2000 % 256
