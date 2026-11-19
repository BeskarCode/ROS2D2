# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 only drives where a sensor looks: forward, steering and backing up are limited to the
directions the sensors in use (and reporting) cover, as placed in sensors.yaml."""
import math
import os

from r2_nav.follow_core import Follower
from r2_nav.modes import parse_modes
from r2_nav.nav_core import Navigator, parse_nav, sees
from r2_sensors.config import load_sensors

ALL = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))
FRONT_ONLY = {n: ALL[n] for n in ("tof_front", "tof_floor")}           # one ToF ahead, +-12.5 deg
NO_REAR = {n: s for n, s in ALL.items() if n not in ("sonar_rear", "lidar")}
FLOOR = 0.28 / math.sin(math.radians(40))


def ranges_for(sensors, **over):
    r = {n: None for n, s in sensors.items() if s["type"] != "rplidar_c1"}
    if "tof_floor" in r:
        r["tof_floor"] = FLOOR
    r.update(over)
    return r


def run(nav, sensors, steps, pose=(0.0, 0.0, 0.0), scan=None, **over):
    return [nav.step(i * 0.1, pose, scan, ranges_for(sensors, **over), True) for i in range(steps)]


def test_sees_follows_the_placement():
    r = ranges_for(FRONT_ONLY)
    assert sees(FRONT_ONLY, 0.0, False, r)
    assert not sees(FRONT_ONLY, math.radians(30), False, r)
    assert not sees(FRONT_ONLY, math.pi, False, r)
    assert not sees(FRONT_ONLY, math.radians(40), False, {})          # not reporting: sees nothing
    assert not sees(FRONT_ONLY, 0.0, False, {"tof_floor": FLOOR})     # a floor sensor does not count


def test_lidar_view_and_blind_sectors():
    lidar = dict(ALL["lidar"], blind_sectors=[[20.0, 40.0]])
    s = {"lidar": lidar}
    assert sees(s, 0.0, True, {}) and sees(s, math.radians(90), True, {})
    assert not sees(s, math.radians(30), True, {})                   # blind sector (R2's leg)
    assert not sees(s, math.pi, True, {})                            # outside its 200 deg
    assert not sees(s, 0.0, False, {})                               # silent lidar: sees nothing


def test_goal_off_to_the_side_turns_first():
    nav = Navigator(parse_nav(""), FRONT_ONLY)
    nav.set_goal(0.0, 2.0)                                           # 90 deg left, nothing looks there
    for d in run(nav, FRONT_ONLY, 20):
        assert d.heading is None or abs(d.heading) <= math.radians(12.5) + 1e-6
        assert d.w > 0                                               # turning towards it
        assert d.v <= 0.35 * math.cos(math.radians(10)) + 1e-9


def test_no_view_ahead_no_forward():
    sides = {n: ALL[n] for n in ("sonar_left", "sonar_right", "sonar_rear")}
    nav = Navigator(parse_nav(""), sides)
    nav.set_goal(2.0, 0.0)
    d = run(nav, sides, 3)[-1]
    assert d.v == 0 and d.hard_stop and "ahead" in d.why
    nav.start_forward(0.0)
    d = run(nav, sides, 3)[-1]
    assert d.v == 0 and d.hard_stop


def test_no_view_behind_no_reverse():
    nav = Navigator(parse_nav("on_blocked: reverse"), NO_REAR)
    nav.set_goal(2.0, 0.0)
    ds = run(nav, NO_REAR, 30, tof_front=0.2)
    assert all(d.v >= 0 for d in ds)
    assert all(d.state != "reversing" for d in ds)
    assert "not backing up" in ds[0].why


def test_lidar_behind_allows_reverse():
    lidar = dict(ALL["lidar"], fov_deg=360)
    s = dict(NO_REAR, lidar=lidar)
    nav = Navigator(parse_nav("on_blocked: reverse"), s)
    nav.set_goal(2.0, 0.0)
    d = run(nav, s, 1, scan=[], tof_front=0.2)[0]
    assert d.state == "reversing" and d.v < 0
    nav = Navigator(parse_nav("on_blocked: reverse"), s)            # something right behind: no
    nav.set_goal(2.0, 0.0)
    d = run(nav, s, 1, scan=[(-0.45, 0.0)], tof_front=0.2)[0]
    assert d.v >= 0


def test_follow_only_where_it_sees():
    f = Follower(parse_modes("")["follow"], parse_nav(""), FRONT_ONLY)
    out = []
    for i in range(40):
        t = i * 0.1
        mk = {"seen": True, "bearing": math.radians(35), "area": 0.01, "cx": 0.5, "cy": 0.5, "t": t}
        out.append(f.step(t, mk, None, ranges_for(FRONT_ONLY)))
    assert all(d.v == 0 for d in out)                                # 35 deg: nothing looks there
    assert any(d.w > 0 for d in out)                                 # it turns towards it instead
