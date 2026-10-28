# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math
import os
import re

import pytest

from r2_nav.nav_core import (NavConfigError, Navigator, RangeFilter, choose_heading, clearance,
                             parse_nav, stop_distances)
from r2_sensors.config import load_sensors

SENSORS = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))
FRONT = ["tof_front_left", "tof_front", "tof_front_right", "sonar_front_left", "sonar_front_right"]


def cfg(**over):
    c = parse_nav("")
    c.update(over)
    return c


def clear_ranges(**over):
    r = {n: None for n in SENSORS if n != "lidar"}
    r.update(over)
    return r


def run(nav, steps, pose=(0.0, 0.0, 0.0), scan=None, ranges=None, auto=True, t0=0.0, dt=0.1):
    out = []
    for i in range(steps):
        out.append(nav.step(t0 + i * dt, pose, [] if scan is None else scan, clear_ranges() if ranges is None else ranges, auto))
    return out


# ---------- nav.yaml ----------

def test_defaults():
    c = parse_nav("")
    assert c["max_turn_deg"] == 30 and c["safety_radius"] == 0.55 and c["sounds"]["give_up"] == "S1:$41"


@pytest.mark.parametrize("text,needle", [
    ("safety_radius: 0\n", "safety_radius"),
    ("max_speed: -1\n", "max_speed"),
    ("give_up_after: 0\n", "give_up_after"),
    ("on_blocked: fly\n", "on_blocked"),
    ("sounds: {blocked: 'rm -rf'}\n", "sounds.blocked"),
    ("a: [1\n", "YAML"),
])
def test_bad_nav_yaml(text, needle):
    with pytest.raises(NavConfigError, match=re.escape(needle)):
        parse_nav(text)


# ---------- stop distances from the safety circle ----------

def test_stop_from_circle():
    s = stop_distances(SENSORS, cfg())
    assert s["tof_front"] == pytest.approx(0.32, abs=0.005)
    assert s["sonar_front_left"] == pytest.approx(0.35)            # its own, larger
    assert s["tof_floor"] == 0 and s["lidar"] == 0
    s2 = stop_distances(SENSORS, cfg(sensors_may_stop_earlier=False))
    assert s2["sonar_front_left"] == pytest.approx(0.3115, abs=0.005)


# ---------- filter ----------

def test_filter_ignores_one_ghost():
    f = RangeFilter()
    for v in [1.0, 1.0, 0.2, 1.0, 1.0]:
        out = f.update(v)
    assert out == pytest.approx(1.0, abs=0.05)


def test_filter_needs_three():
    f = RangeFilter()
    outs = [f.update(v) for v in [None, None, 1.0]]
    assert outs[-1] is None


# ---------- heading ----------

def test_clearance_and_heading():
    pts = [(1.0, 0.0)]                                              # something 1 m ahead
    assert clearance(pts, 0.0) == pytest.approx(1.0)
    assert clearance(pts, math.radians(90)) == 3.0
    h, c = choose_heading([(0.6, 0.0), (0.6, 0.1), (0.6, -0.1)], 0.0, cfg())
    assert abs(h) >= math.radians(20) and c > 0.6


# ---------- the navigator ----------

def test_goes_straight_when_clear():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 3)[-1]
    assert d.state == "going" and d.v > 0 and abs(d.w) < 0.05


def test_manual_without_auto_mode():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 3, auto=False)[-1]
    assert (d.v, d.w, d.state) == (0, 0, "manual")


def test_no_data_no_motion():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = nav.step(0.0, (0, 0, 0), None, {}, True)
    assert d.v == 0 and d.state == "no data"


def test_stops_before_circle():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 1, ranges=clear_ranges(tof_front=0.30))[-1]
    assert d.state == "stop" and d.v == 0 and "blocked" in d.events


def test_turns_one_way():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    ds = run(nav, 10, ranges=clear_ranges(tof_front=0.2))
    signs = {math.copysign(1, d.w) for d in ds}
    assert len(signs) == 1 and all(d.v == 0 for d in ds)


def test_reverse_only_if_allowed():
    nav = Navigator(cfg(on_blocked="reverse", allow_reverse=False), SENSORS)
    nav.set_goal(2.0, 0.0)
    assert all(d.v >= 0 for d in run(nav, 20, ranges=clear_ranges(tof_front=0.2)))


def test_reverse_backs_up_then_turns():
    nav = Navigator(cfg(on_blocked="reverse"), SENSORS)
    nav.set_goal(2.0, 0.0)
    ds = run(nav, 40, ranges=clear_ranges(tof_front=0.2))
    assert ds[0].state == "reversing" and ds[0].v < 0
    assert sum(1 for d in ds if d.state == "reversing") <= 21          # 0.30 m at 0.15 m/s
    assert ds[-1].state in ("stop", "turning")


def test_reverse_watches_rear():
    nav = Navigator(cfg(on_blocked="reverse"), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 1, ranges=clear_ranges(tof_front=0.2, sonar_rear=0.1))[-1]
    assert d.v >= 0 and d.state in ("stop", "turning")


def test_waits_then_turns():
    nav = Navigator(cfg(on_blocked="wait"), SENSORS)
    nav.set_goal(2.0, 0.0)
    ds = run(nav, 50, ranges=clear_ranges(tof_front=0.2))
    assert ds[0].state == "waiting" and ds[0].v == 0 and ds[0].w == 0
    assert ds[-1].state in ("stop", "turning")


def test_gives_up_and_stays():
    nav = Navigator(cfg(give_up_after=2), SENSORS)
    nav.set_goal(2.0, 0.0)
    t = 0.0
    events = []
    for _ in range(3):                                              # three times blocked, freed in between
        for d in run(nav, 3, ranges=clear_ranges(tof_front=0.2), t0=t):
            events += d.events
        t += 0.3
        for d in run(nav, 15, t0=t):
            events += d.events
        t += 1.5
    last = run(nav, 100, t0=t)
    assert "give_up" in events and all(d.v == 0 and d.state == "gave up" for d in last)
    nav.set_goal(2.0, 0.0)
    assert run(nav, 2, t0=t + 20)[-1].state == "going"


def test_blocks_while_making_progress_do_not_give_up():
    # skirting a table: briefly blocked again and again, but getting closer each time
    nav = Navigator(cfg(give_up_after=2), SENSORS)
    nav.set_goal(4.0, 0.0)
    t, x = 0.0, 0.0
    states = []
    for _ in range(5):
        states += [d.state for d in run(nav, 2, pose=(x, 0, 0), ranges=clear_ranges(tof_front=0.2), t0=t)]
        t += 0.2
        states += [d.state for d in run(nav, 10, pose=(x, 0, 0), t0=t)]
        t += 1.0
        x += 0.6                                                    # 0.6 m closer before the next block
    assert "gave up" not in states


def test_watchdog_counts_a_try():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    run(nav, 130)                                                   # 13 s without getting closer
    assert nav.tries == 1


def test_arrived_event():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 1, pose=(1.8, 0.0, 0.0))[-1]
    assert d.state == "arrived" and "arrived" in d.events and d.v == 0


def test_obstacle_event_throttled():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    ds = run(nav, 20, ranges=clear_ranges(tof_front=0.6))
    assert sum(d.events.count("obstacle") for d in ds) == 1


def test_auto_on_event():
    nav = Navigator(cfg(), SENSORS)
    run(nav, 2, auto=False)
    assert "auto_on" in run(nav, 1, auto=True)[-1].events
