# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Dead reckoning from what went to the Mega, with the IMU's heading."""
import math

import pytest

from r2_nav.odometry import DeadReckoning, parse_foot, yaw_of


def run(dr, seconds, dt=0.1, t0=0.0, foot=None, imu=None):
    t = t0
    while t < t0 + seconds - 1e-9:
        t += dt
        if foot:
            dr.on_foot(t, *foot)
        if imu:
            dr.on_imu(t, imu(t))
        dr.step(t)
    return t


def test_parse_foot():
    assert parse_foot("ROS:FOOT:20,-5\n") == (20, -5)
    assert parse_foot("ROS:DOME:20") is None and parse_foot("ROS:FOOT:x") is None


def test_straight_at_the_calibrated_speed():
    dr = DeadReckoning(drive_per_mps=50)
    dr.step(0.0)
    run(dr, 2.0, foot=(10, 0))                       # 10 units = 0.2 m/s for 2 s
    assert dr.x == pytest.approx(0.4, abs=0.02) and abs(dr.y) < 1e-9


def test_stops_when_the_mega_would():
    dr = DeadReckoning()
    dr.step(0.0)
    dr.on_foot(0.0, 10, 0)
    for k in range(1, 11):                           # no new command: the Mega stops after 0.3 s
        dr.step(0.1 * k)
    assert dr.x == pytest.approx(0.2 * 0.3, abs=0.021)


def test_heading_from_the_imu_wins():
    dr = DeadReckoning(turn_per_radps=30)
    dr.step(0.0)
    # the feet are told to turn, but the IMU says it did not (slipping): heading stays
    run(dr, 1.0, foot=(0, 15), imu=lambda t: 0.3)
    assert dr.th == pytest.approx(0.0, abs=1e-9)
    run(dr, 1.0, t0=1.0, foot=(0, 0), imu=lambda t: 0.3 + 0.5 * (t - 1.0))   # now it really turns 0.5 rad
    assert dr.th == pytest.approx(0.5, abs=0.06)


def test_without_imu_the_commanded_turn():
    dr = DeadReckoning(turn_per_radps=30)
    dr.step(0.0)
    run(dr, 1.0, foot=(0, 15))                       # 0.5 rad/s for 1 s
    assert dr.th == pytest.approx(0.5, abs=0.06)


def test_yaw_of():
    assert yaw_of(0, 0, math.sin(0.4), math.cos(0.4)) == pytest.approx(0.8)
