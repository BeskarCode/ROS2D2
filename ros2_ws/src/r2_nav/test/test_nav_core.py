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


FLOOR = 0.28 / math.sin(math.radians(40))      # what the floor ToF reads on a flat floor


def clear_ranges(**over):
    r = {n: None for n in SENSORS if n != "lidar"}
    r["tof_floor"] = FLOOR
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
    assert c["max_turn_deg"] == 15 and c["safety_radius"] == 0.55 and c["sounds"]["give_up"] == "S1:$41"
    # a 40 kg droid: gentle ramps, and power caps like ShadowMD's drivespeed / turnspeed
    assert c["accel"] == 0.25 and c["turn_accel_deg"] == 20
    assert c["max_drive_power"] == 40 and c["max_turn_power"] == 30


def test_power_caps_speed_and_turn():
    nav = Navigator(cfg(max_drive_power=10, max_turn_power=6), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 3)[-1]
    assert 0 < d.v <= 10 / 50 + 1e-9                                 # 10 units at 50 units per m/s
    nav.set_goal(0.0, 2.0)                                          # 90 degrees to the left: a big turn
    d = run(nav, 1)[-1]
    assert 0 < d.w <= 6 / 30 + 1e-9


def test_braking_distance_counts():
    # at 0.3 m/s with 0.25 m/s² it needs 0.18 m to stop: 0.45 m ahead is already too close
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = nav.step(0.0, (0, 0, 0), [], clear_ranges(tof_front=0.45), True, speed=0.3)
    assert d.state == "stop" and d.stops["tof_front"] == pytest.approx(0.32 + 0.18, abs=0.01)
    d2 = Navigator(cfg(), SENSORS)
    d2.set_goal(2.0, 0.0)
    assert d2.step(0.0, (0, 0, 0), [], clear_ranges(tof_front=0.45), True, speed=0.0).state != "stop"


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
    assert s["tof_floor"] == pytest.approx(FLOOR * 0.8) and s["lidar"] == 0     # shorter = something low
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


# ---------- the floor sensor ----------

def test_floor_sensor_stops_for_something_low():
    # a box under the lidar's plane cuts the floor beam short
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 1, ranges=clear_ranges(tof_floor=0.30))[-1]
    assert d.state == "stop" and d.v == 0 and "tof_floor" in d.why


@pytest.mark.parametrize("reading", [None, FLOOR * 1.6])
def test_floor_sensor_stops_at_a_drop(reading):
    # no floor where there should be one: a step down or a hole
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    run(nav, 1)                                                          # it has seen the floor
    d = run(nav, 1, ranges=clear_ranges(tof_floor=reading), t0=0.1)[-1]
    assert d.state == "stop" and d.v == 0 and "floor" in d.why


def test_floor_sensor_on_a_flat_floor_lets_it_go():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    assert run(nav, 3, ranges=clear_ranges(tof_floor=FLOOR * 1.05))[-1].v > 0
    nav2 = Navigator(cfg(), SENSORS)
    nav2.set_goal(2.0, 0.0)
    r = clear_ranges()
    del r["tof_floor"]                                       # not reporting: it does not stop R2
    assert run(nav2, 3, ranges=r)[-1].v > 0


def test_drifting_away_from_the_goal_counts_a_try():
    # steering round things must not become a walk away from the goal: 0.5 m further than the
    # closest it got counts as a failed try (and enough of them make it give up)
    nav = Navigator(cfg(give_up_after=1), SENSORS)
    nav.set_goal(1.0, 0.0)
    nav.step(0.0, (0.6, 0.0, 0.0), [], clear_ranges(), True)            # 0.4 m to go
    d = nav.step(0.1, (0.2, 0.0, 0.0), [], clear_ranges(), True)        # 0.8 m: not yet
    assert d.tries == 0
    d = nav.step(0.2, (0.0, 0.0, 0.0), [], clear_ranges(), True)        # 1.0 m: 0.6 further
    assert d.tries == 1 and "blocked" in d.events
    nav.step(0.3, (0.0, 0.0, 0.0), [], clear_ranges(), True)
    d = nav.step(0.4, (-0.6, 0.0, 0.0), [], clear_ranges(), True)       # again: second try > 1
    assert d.state == "gave up"


def test_slows_down_near_things_even_beside_its_path():
    # something 0.7 m away at 45 deg is not in the way, but R2 goes slower past it
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(3.0, 0.0)
    free = run(nav, 3)[-1].v
    nav2 = Navigator(cfg(), SENSORS)
    nav2.set_goal(3.0, 0.0)
    near = run(nav2, 3, scan=[(0.5, 0.5)])[-1].v
    assert free == pytest.approx(cfg()["max_speed"]) and 0 < near <= 0.5 * free


def test_floor_sensor_without_a_first_reading_does_not_stop():
    # the filter needs 3 readings: 'nothing yet' at start-up is not 'no floor'
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 2, ranges=clear_ranges(tof_floor=None))[-1]
    assert d.state != "stop" and d.tries == 0
    run(nav, 1, ranges=clear_ranges())                                   # it has seen the floor
    assert run(nav, 1, ranges=clear_ranges(tof_floor=None), t0=1.0)[-1].state == "stop"


def test_coming_back_to_where_it_was_does_not_start_the_count_again():
    # wander off (a try, 1.6 m to go), come back to 1.1 m and get blocked there: 0.5 m closer
    # than the last try, but not closer than it ever was (1.0 m), so the count goes on
    nav = Navigator(cfg(give_up_after=1), SENSORS)
    nav.set_goal(2.0, 0.0)
    nav.step(0.0, (1.0, 0.0, 0.0), [], clear_ranges(), True)
    assert nav.step(0.1, (0.4, 0.0, 0.0), [], clear_ranges(), True).tries == 1
    d = nav.step(0.2, (0.9, 0.0, 0.0), [], clear_ranges(tof_front=0.1), True)
    assert d.state == "gave up"


# ---------- ignored sensors (enabled: false) ----------
from r2_nav.nav_core import state_json  # noqa: E402
from r2_sensors.config import in_use  # noqa: E402


def test_reconfigure_with_no_sensors_in_use():
    nav = Navigator(cfg(), SENSORS)
    nav.reconfigure(sensors={})
    assert nav.sensors == {}


def test_ignored_front_sensor_does_not_stop():
    nav = Navigator(cfg(), SENSORS)
    nav.set_goal(2.0, 0.0)
    d = run(nav, 1, ranges=clear_ranges(tof_front=0.10))[-1]
    assert d.state == "stop" and "tof_front" in d.why
    ignored = {n: ({**s, "enabled": False} if n == "tof_front" else s) for n, s in SENSORS.items()}
    nav2 = Navigator(cfg(), in_use(ignored))
    nav2.set_goal(2.0, 0.0)
    d2 = run(nav2, 1, ranges=clear_ranges(tof_front=0.10))[-1]
    assert "tof_front" not in (d2.why or "")


def test_ignored_lidar_counts_as_no_lidar():
    from r2_nav.lidar_gate import motor_policy
    s = {n: ({**v, "enabled": False, "motor": "with_modes"} if n == "lidar" else v) for n, v in SENSORS.items()}
    assert motor_policy(in_use(s)) == "always"


def test_state_json_lists_ignored():
    nav = Navigator(cfg(), SENSORS)
    d = run(nav, 1)[-1]
    import json
    assert json.loads(state_json(d, None, None, {}, {}, ignored=["tof_front"]))["ignored"] == ["tof_front"]


# ---------- Go forward ----------
from r2_nav.nav_core import SEARCH_TURN, wrap  # noqa: E402


def wm_of(c):
    return min(math.radians(c["max_turn_deg"]), c["max_turn_power"] / 30)


def wall_ahead(at=0.45, half=0.6):
    return [(at, y / 20) for y in range(int(-half * 20), int(half * 20) + 1)]


def test_forward_drives_straight_in_open_room():
    nav = Navigator(cfg(), SENSORS)
    nav.start_forward(0.0)
    d = run(nav, 20)[-1]
    assert d.state == "forward" and d.v > 0.1 and abs(d.w) < 0.01


def test_forward_keeps_its_heading_after_steering():
    nav = Navigator(cfg(), SENSORS)
    nav.start_forward(0.0)
    d = run(nav, 5, pose=(0.0, 0.0, 0.3))[-1]          # pushed 17 deg left: steers back right
    assert d.state == "forward" and d.w < 0


def test_forward_turns_slowly_when_blocked_and_leaves_by_the_gap():
    c = cfg()
    nav = Navigator(c, SENSORS)
    nav.start_forward(0.0)
    left_free = wall_ahead() + [(0.2 + k / 10, -0.5) for k in range(10)]   # something on the right too
    d = run(nav, 3, scan=left_free)[-1]
    assert d.state == "searching" and d.v == 0
    assert 0 < d.w <= SEARCH_TURN * wm_of(c) + 1e-9       # slowly, towards the free side
    d = run(nav, 3, pose=(0.0, 0.0, 1.2), t0=1.0)[-1]   # turned 69 deg: nothing ahead now
    assert d.state == "forward" and d.v > 0
    assert nav.forward_th == pytest.approx(1.2)


def test_forward_gives_up_after_a_full_turn():
    c = cfg()
    nav = Navigator(c, SENSORS)
    nav.start_forward(0.0)
    boxed = [(0.45 * math.cos(math.radians(a)), 0.45 * math.sin(math.radians(a))) for a in range(0, 360, 5)]
    th, t, events, turned = 0.0, 0.0, [], 0.0
    for _ in range(3000):
        d = nav.step(t, (0.0, 0.0, th), boxed, clear_ranges(), True)
        events += d.events
        if d.state == "gave up":
            break
        assert d.v <= 0                                  # never into the box
        th = wrap(th + d.w * 0.1)
        turned += abs(d.w * 0.1)
        t += 0.1
    assert d.state == "gave up" and "give_up" in events
    assert turned >= 2 * math.pi - 0.1
    assert d.v == 0 and d.w == 0 and nav.forward_th is None


def test_forward_with_no_data_does_not_move():
    nav = Navigator(cfg(), SENSORS)
    nav.start_forward(0.0)
    d = nav.step(0.0, (0.0, 0.0, 0.0), None, {}, True)
    assert d.state == "no data" and d.v == 0 and d.w == 0


def test_cancel_stops_forward():
    nav = Navigator(cfg(), SENSORS)
    nav.start_forward(0.0)
    nav.cancel()
    assert nav.forward_th is None and run(nav, 2)[-1].state == "idle"
