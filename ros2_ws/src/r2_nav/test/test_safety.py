# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigation's safety: hard stops, sensors that go silent, no odometry, how old each input
is, safe limits, the distance sensors' cones and the shared inputs and ramps (shaping)."""
import math
import os

import pytest

from r2_nav.nav_core import NavConfigError, Navigator, parse_nav, points_from, state_json
from r2_nav.shaping import SensorInputs, shape
from r2_sensors.config import load_sensors

SENSORS = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))
FLOOR = 0.28 / math.sin(math.radians(40))


def cfg(**over):
    c = parse_nav("")
    c.update(over)
    return c


def clear(**over):
    r = {n: None for n in SENSORS if n != "lidar"}
    r["tof_floor"] = FLOOR
    r.update(over)
    return r


# ---------- 1 · a stop is a stop ----------

def test_something_in_the_safety_circle_stops_at_once():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(3.0, 0.0)
    d = nav.step(0.0, (0.0, 0.0, 0.0), [(0.45, 0.0)], clear(), True, speed=0.35)   # someone steps in, 0.45 m ahead
    assert d.v == 0 and d.hard_stop
    v, _ = shape((0.35, 0.0), d.v, d.w, d.hard_stop, cfg(), 0.1)
    assert v == 0.0                                  # in one tick, not 1.4 s of ramp


@pytest.mark.parametrize("state_maker", ["no data", "gave up", "waiting", "reversing", "searching"])
def test_every_stop_of_the_logic_is_a_hard_stop(state_maker):
    c = cfg(on_blocked={"waiting": "wait", "reversing": "reverse"}.get(state_maker, "turn"))
    nav = Navigator(c, SENSORS)
    pose = (0.0, 0.0, 0.0)
    if state_maker == "no data":
        nav.set_goal(3.0, 0.0)
        d = nav.step(0.0, pose, None, {}, True)
    elif state_maker == "gave up":
        nav.gave_up = "test"
        d = nav.step(0.0, pose, [], clear(), True)
    elif state_maker == "searching":
        nav.start_forward(0.0)
        d = nav.step(0.0, pose, [(0.45, 0.0)], clear(), True)
    else:
        nav.set_goal(3.0, 0.0)
        d = nav.step(0.0, pose, [(0.45, 0.0)], clear(sonar_rear=None), True)
    assert d.state == state_maker and d.hard_stop, (d.state, d.why)


def test_a_soft_slow_down_keeps_its_ramp():
    v, _ = shape((0.35, 0.0), 0.1, 0.0, False, cfg(decel=0.25), 0.1)
    assert v == pytest.approx(0.325)                 # 0.25 m/s² for 0.1 s
    v, _ = shape((0.35, 0.0), 0.1, 0.0, False, cfg(decel=1.0), 0.1)
    assert v == pytest.approx(0.25)


def test_a_hard_stop_keeps_turning_smooth_and_may_still_reverse():
    v, w = shape((0.3, 0.2), 0.0, 0.0, True, cfg(), 0.1)
    assert v == 0.0 and 0 < w < 0.2                  # turning ramps down
    v, _ = shape((0.3, 0.0), -0.15, 0.0, True, cfg(), 0.1)
    assert v <= 0.0                                  # backing up starts from a standstill, not from 0.3


def test_the_lidar_also_counts_the_braking_distance():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(3.0, 0.0)
    pts = [(0.62, 0.0)]                              # just outside the 0.55 circle
    assert not nav.step(0.0, (0, 0, 0), pts, clear(), True, speed=0.0).hard_stop
    nav2 = Navigator(cfg(), SENSORS)
    nav2.set_goal(3.0, 0.0)
    assert nav2.step(0.0, (0, 0, 0), pts, clear(), True, speed=0.35).hard_stop   # 0.245 m to stop: too close


def test_braking_uses_the_measured_deceleration_not_accel():
    from r2_nav.nav_core import braking
    assert braking(0.35, cfg(accel=2.0, brake_decel=0.25)) == pytest.approx(0.245)


# ---------- 3 · a sensor that goes silent is lost, not "nothing there" ----------

@pytest.mark.parametrize("name", ["tof_front", "tof_floor", "lidar"])
def test_a_sensor_that_went_silent_stops_it(name):
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(3.0, 0.0)
    d = nav.step(0.0, (0, 0, 0), [], clear(), True, lost=[name])
    assert d.state == "sensor lost" and d.v == 0 and d.hard_stop and d.lost == [name]
    assert name in d.why


def test_a_lost_rear_or_ignored_sensor_does_not_stop_it():
    nav = Navigator(cfg(), {k: v for k, v in SENSORS.items() if k != "tof_front"})   # tof_front ignored
    nav.set_goal(3.0, 0.0)
    assert nav.step(0.0, (0, 0, 0), [], clear(), True, lost=["sonar_rear", "tof_front"]).state != "sensor lost"


def test_inputs_lost_ages_and_filter_reset():
    i = SensorInputs()
    for k in range(5):
        i.on_range("tof_front", k * 0.05, 1.0)
    s = i.snapshot(0.25)
    assert s.ranges["tof_front"] == pytest.approx(1.0) and s.lost == [] and s.ages["tof_front"] == pytest.approx(0.05)
    s = i.snapshot(0.9)                              # 0.7 s without a reading
    assert "tof_front" not in s.ranges and s.lost == ["tof_front"]
    i.on_range("tof_front", 1.0, 0.4)                # back: the old 1.0 m readings are gone
    assert i.snapshot(1.0).ranges["tof_front"] is None   # needs 3 new readings before it believes again


def test_the_filter_runs_on_every_reading_not_on_the_tick():
    i = SensorInputs()
    for k in range(3):                               # 3 readings between two ticks (a fast ToF)
        i.on_range("tof_front", 0.01 * k, 0.8)
    assert i.snapshot(0.05).ranges["tof_front"] == pytest.approx(0.8)


def test_the_lidar_is_lost_only_after_it_scanned_in_this_mode():
    i = SensorInputs()
    i.on_scan(0.0, [(1.0, 0.0)])
    i.arm(5.0)                                       # mode on later: the motor (with_modes) was off
    assert i.snapshot(6.0, "lidar").lost == []       # not spinning yet: the gate waits, not "lost"
    i.on_scan(9.0, [(1.0, 0.0)])
    assert i.snapshot(10.0, "lidar").lost == ["lidar"]


# ---------- 2 · no odometry ----------

def test_without_odometry_it_does_not_move():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(3.0, 0.0)
    d = nav.step(0.0, None, [], clear(), True)
    assert d.state == "no odom" and d.v == 0 and d.hard_stop
    nav = Navigator(cfg(), SENSORS)
    nav.start_forward(0.0)
    assert nav.step(0.0, None, [], clear(), True).state == "no odom"


# ---------- 9 · how old each input is ----------

def test_state_says_how_old_each_input_is():
    nav = Navigator(cfg(), SENSORS)
    d = nav.step(0.0, (0, 0, 0), [], clear(), True)
    j = state_json(d, None, None, {}, {}, sources={"odom": 0.04, "lidar": None, "tof_front": 1.234})
    assert '"sources": {"odom": 0.04, "lidar": null, "tof_front": 1.23}' in j and '"lost": []' in j


# ---------- 6 · safe limits ----------

@pytest.mark.parametrize("text", ["safety_radius: 0.3", "slow_from: 0.1"])
def test_limits_keep_the_circle_outside_the_body(text):
    with pytest.raises(NavConfigError):
        parse_nav(text)


# ---------- 7 · the distance sensors' cones ----------

def test_a_reading_covers_its_cone():
    s = SENSORS["sonar_front_left"]
    pts = points_from(None, {"sonar_front_left": 1.0}, SENSORS)
    half = math.radians(s["fov_deg"]) / 2
    ys = sorted(round(p[1] - s["y"], 3) for p in pts)
    a = math.radians(s["yaw_deg"])
    assert ys == sorted(round(math.sin(a + k), 3) for k in (-half, 0.0, half))


# ---------- 11 · times in seconds ----------

def test_turning_away_counts_seconds_not_ticks():
    c = cfg(free_s=0.8)
    nav = Navigator(c, SENSORS)
    nav.set_goal(3.0, 0.0)
    nav.step(0.0, (0, 0, 0), [(0.45, 0.0)], clear(), True)          # blocked: turning
    states = [nav.step(0.1 + 0.25 * k, (0, 0, 0), [], clear(), True).state for k in range(1, 6)]
    # free for 0.8 s at 0.25 s a tick: turning for 4 ticks (not 8), then heading for the goal
    assert states[:3] == ["turning"] * 3 and states[4] == "going"


def test_follow_stops_when_a_sensor_goes_silent():
    from r2_nav.follow_core import Follower
    from r2_nav.modes import parse_modes
    f = Follower(parse_modes("")["follow"], cfg(), SENSORS)
    f.start(0.0)
    marker = {"seen": True, "t": 2.0, "bearing": 0.0, "area": 0.05}
    d = f.step(2.0, marker, [], clear(), lost=["tof_floor"])
    assert d.state == "sensor lost" and d.v == 0 and d.w == 0
