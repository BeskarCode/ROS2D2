# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math
import os

from r2_nav.follow_core import BLOCKED_AFTER, BLOCKED_REPEAT, DOME_SEARCH, Follower
from r2_nav.modes import parse_modes
from r2_nav.nav_core import parse_nav
from r2_sensors.config import load_sensors

SENSORS = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))
FLOOR = 0.28 / math.sin(math.radians(40))      # what the floor ToF reads on a flat floor
DT = 0.1


def follow_cfg(**over):
    f = parse_modes("")["follow"]
    f.update(over)
    return f


def clear_ranges(**over):
    r = {n: None for n in SENSORS if n != "lidar"}
    r["tof_floor"] = FLOOR
    r.update(over)
    return r


def marker(t, bearing=0.0, area=0.05, seen=True):
    return {"seen": seen, "bearing": bearing, "area": area, "cx": 0.5, "cy": 0.5, "t": t}


def person(dist, bearing=0.0):
    """A few lidar points on someone standing `dist` m away at `bearing`."""
    return [(dist * math.cos(bearing + a), dist * math.sin(bearing + a)) for a in (-0.03, 0.0, 0.03)]


def run(f, steps, scan=None, ranges=None, mk=lambda t: marker(t), t0=0.0):
    out = []
    for i in range(steps):
        t = t0 + i * DT
        out.append(f.step(t, mk(t), [] if scan is None else scan, clear_ranges() if ranges is None else ranges))
    return out


def follower(**over):
    return Follower(follow_cfg(**over), parse_nav(""), SENSORS)


def test_follows_straight():
    d = run(follower(), 20, scan=person(3.0))[-1]
    assert d.v > 0 and abs(d.w) < 1e-6 and d.state == "following" and d.dome == 0


def test_turns_toward_marker():
    d = run(follower(), 10, scan=person(3.0, 0.3), mk=lambda t: marker(t, bearing=0.3))[-1]
    assert d.w > 0


def test_waits_at_distance():
    f = follower(distance=1.5)
    d = run(f, 20, scan=person(1.55))[-1]
    assert d.v == 0 and d.state == "waiting"


def test_follow_never_reverses():
    out = run(follower(), 50, scan=person(0.6))
    assert out[-1].v == 0 and all(d.v >= 0 for d in out)


def test_stale_marker_is_lost():
    f = follower()
    run(f, 20, scan=person(3.0))                        # moving
    d = f.step(2.4, marker(2.0), person(3.0), clear_ranges())   # last marker 0.4 s old
    assert d.v == 0 and d.w == 0 and "lost" in d.events and d.state == "searching"
    d = f.step(2.5, marker(2.0), person(3.0), clear_ranges())
    assert "lost" not in d.events                       # once, not every step


def test_search_returns_to_front():
    f = follower(search_s=5)
    run(f, 5, scan=person(3.0))
    out = run(f, 70, scan=person(3.0), mk=lambda t: None, t0=0.5)
    searching = [d for d in out if d.state == "searching"]
    assert abs(len(searching) * DT - 5) <= 2 * DT
    assert {d.dome for d in searching} == {DOME_SEARCH, -DOME_SEARCH}
    assert isinstance(searching[0].dome, int) and searching[0].dome == DOME_SEARCH
    assert abs(sum(d.dome * DT for d in searching)) <= DOME_SEARCH * 2 * DT
    assert out[-1].state == "lost" and out[-1].dome == 0 and out[-1].v == 0
    assert sum("lost" in d.events for d in out) == 1
    d = f.step(8.0, marker(8.0), person(3.0), clear_ranges())
    assert d.state == "following" and "found" in d.events


def test_obstacle_between_stops():
    # the marker says 3 m (by its size) but something is 0.5 m ahead
    f = follower(area_ref=0.1, distance=1.5)
    out = run(f, 30, scan=person(0.5), mk=lambda t: marker(t, area=0.025))
    assert all(d.v == 0 for d in out) and out[-1].state == "blocked"


def test_size_fallback():
    f = follower(area_ref=0.1, distance=1.5)
    d = run(f, 10, scan=[], mk=lambda t: marker(t, area=0.025))[-1]   # 1.5 * sqrt(0.1 / 0.025) = 3 m
    assert d.v > 0 and d.state == "following"
    d = run(follower(), 10, scan=[], mk=lambda t: marker(t, bearing=0.2))[-1]   # no area_ref: turn only
    assert d.v == 0 and d.w > 0


def test_ramps():
    nav = parse_nav("")
    f = follower(max_speed=0.3)
    out = run(f, 40, scan=person(3.0))
    vs = [d.v for d in out]
    assert max(vs) == 0.3
    first = next(i for i, v in enumerate(vs) if v >= 0.3 - 1e-9)
    assert (first + 1) * DT >= 0.3 / nav["accel"] - 1e-6
    assert all(b - a <= nav["accel"] * DT + 1e-9 for a, b in zip([0.0] + vs, vs))


def test_blocked_repeats_sound():
    f = follower(area_ref=0.1, distance=1.5)
    out = run(f, 200, scan=[], ranges=clear_ranges(tof_front=0.1), mk=lambda t: marker(t, area=0.025))
    times = [i * DT for i, d in enumerate(out) if "blocked" in d.events]
    assert len(times) == 2
    assert abs(times[0] - BLOCKED_AFTER) <= 2 * DT and abs(times[1] - BLOCKED_AFTER - BLOCKED_REPEAT) <= 2 * DT
    assert all(d.v == 0 for d in out) and all(d.state == "blocked" for d in out)


def test_no_data():
    f = follower()
    d = f.step(0.0, marker(0.0), None, {})
    assert d.state == "no data" and d.v == 0 and d.w == 0 and d.dome == 0
