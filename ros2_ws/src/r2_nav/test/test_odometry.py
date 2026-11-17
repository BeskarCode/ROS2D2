# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Dead reckoning from what went to the Mega, with the IMU's heading."""
import math

import pytest

from r2_nav.odometry import DeadReckoning, parse_foot, yaw_of


def run(dr, seconds, dt=0.1, t0=0.0, foot=None, imu=None, laser=None):
    t = t0
    while t < t0 + seconds - 1e-9:
        t += dt
        if foot:
            dr.on_foot(t, *foot)
        if imu:
            dr.on_imu(t, imu(t))
        if laser:
            dr.on_laser(t, *laser(t))
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


# ---------- laser odometry (rf2o on /scan) corrects the slips ----------

def test_laser_odometry_moves_it_when_the_feet_slip():
    dr = DeadReckoning(drive_per_mps=50)
    dr.step(0.0)
    # the Mega is told 0.2 m/s, but the lidar sees R2 move only 0.05 m/s (wheels slipping)
    run(dr, 2.0, foot=(10, 0), laser=lambda t: (0.05 * t, 0.0, 0.0))
    # the first tick has no laser step yet (the commands: 0.02 m), then the lidar's 0.005 m a tick
    assert dr.x == pytest.approx(0.02 + 19 * 0.005, abs=0.005)


def test_laser_steps_are_turned_into_our_heading():
    dr = DeadReckoning()
    dr.step(0.0)
    dr.th = math.pi / 2                              # we think R2 faces +y
    # rf2o's own frame starts facing +x: moving 0.3 m ahead there is 0.3 m along +y here
    run(dr, 1.0, laser=lambda t: (0.3 * t, 0.0, 0.0), imu=lambda t: 0.0)
    assert dr.y == pytest.approx(0.27, abs=0.01) and abs(dr.x) < 0.01   # 9 laser steps of 0.03 m


def test_without_imu_the_laser_gives_the_heading():
    dr = DeadReckoning(turn_per_radps=30)
    dr.step(0.0)
    run(dr, 1.0, foot=(0, 15), laser=lambda t: (0.0, 0.0, 0.2 * t))   # told 0.5 rad/s, really 0.2
    assert dr.th == pytest.approx(0.2, abs=0.03)


def test_a_stale_laser_falls_back_to_the_commands():
    dr = DeadReckoning(drive_per_mps=50)
    dr.step(0.0)
    dr.on_laser(0.0, 0.0, 0.0, 0.0)                  # one message, then silence
    run(dr, 1.0, foot=(10, 0))
    # while it is fresh (0.3 s) the lidar says "not moving"; then the commands, 0.02 m a tick
    assert dr.x == pytest.approx(0.2 - 2 * 0.02, abs=0.021)
