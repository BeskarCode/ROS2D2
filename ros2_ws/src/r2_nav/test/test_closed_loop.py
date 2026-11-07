# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigator driving the simulated R2 round the simulated room, without ROS (closed_loop.py):
the same checks as docker/nav_bench.sh, deterministic and in seconds."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
world_mod = pytest.importorskip("r2_sim.world")
pytest.importorskip("r2_shadow_bridge.protocol")
from closed_loop import drive, follow  # noqa: E402
from r2_sensors.config import load_sensors  # noqa: E402

SENSORS = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_reaches_a_goal_round_the_table(seed):
    w = world_mod.World.default()
    w.apply({"op": "remove", "id": 4})                     # the person: leave a clear way round
    trace = drive(w, SENSORS, (2.2, 1.2), seed=seed)
    assert trace[-1][1] == "arrived", trace[-1]
    assert trace[-1][0] < 60


def test_gives_up_on_a_goal_behind_the_wall():
    trace = drive(world_mod.World.default(), SENSORS, (-3.4, -1.2), seconds=200)
    assert trace[-1][1] == "gave up", trace[-1]


@pytest.mark.parametrize("goal", [(2.2, 1.2), (-3.4, -1.2), (1.6, -1.5)])
def test_never_drives_into_things(goal):
    # the room stops R2 if it drives into something: that must never be needed
    trace = drive(world_mod.World.default(), SENSORS, goal, seconds=120, seed=4)
    bumps = [row[:6] for row in trace if row[7]]
    assert bumps == []


def test_turns_are_smooth():
    # what reaches the feet never changes its turn rate faster than turn_accel_deg allows
    trace = drive(world_mod.World.default(), SENSORS, (2.2, 1.2), seconds=60, seed=2)
    limit = math.radians(20) * 0.1 + 1 / 30 + 1e-6            # one step of the ramp + one Sabertooth unit
    jumps = [abs(b[9] - a[9]) for a, b in zip(trace, trace[1:])]
    assert max(jumps) <= limit, max(jumps)


def _follow_world(person, box=None):
    w = world_mod.World.empty()
    w.pose = [-2.6, 0.0, 0.0]
    w.apply(dict(person, op="add", kind="post", r=0.15, height=1.7, marker=True))
    if box:
        w.apply(dict(box, op="add", kind="box"))
    return w


def _area_ref(distance):
    # what the camera sees of a person at `distance`, so the size fallback agrees with the room
    w = world_mod.World.empty()
    w.apply({"op": "add", "kind": "post", "x": distance, "y": 0.0, "marker": True})
    return w.marker_view((0.0, 0.0, 0.0))["area"]


def test_closed_loop_follow():
    # the person walks 3 m away in a straight line: R2 ends 1.5 m behind, never inside the safety circle
    from r2_nav.modes import parse_modes
    from r2_nav.nav_core import parse_nav
    fcfg = parse_modes("")["follow"]
    fcfg["area_ref"] = _area_ref(fcfg["distance"])
    w = _follow_world({"x": -0.8, "y": 0.0})
    trace = follow(w, SENSORS, lambda t: (min(-0.8 + 0.15 * t, 2.2), 0.0), seconds=45, fcfg=fcfg)
    assert abs(trace[-1][4] - 1.5) <= 0.3, trace[-1]
    assert trace[-1][3] == pytest.approx(0.0, abs=0.3)
    assert min(row[4] for row in trace) >= parse_nav("")["safety_radius"]
    assert not any(row[5] for row in trace)


def test_closed_loop_follow_stops_behind_a_box():
    # the person steps behind a tall box: R2 loses it and stops
    box = {"x": -0.5, "y": 0.0, "w": 0.6, "h": 0.6, "height": 1.3}
    w = _follow_world({"x": 1.0, "y": -1.3}, box)
    trace = follow(w, SENSORS, lambda t: (1.0, -1.3) if t < 1.5 else (1.0, 0.0), seconds=20)
    assert trace[-1][6] == 0.0 and trace[-1][1] in ("searching", "lost"), trace[-1]
    assert not any(row[5] for row in trace)
    assert math.hypot(trace[-1][2] + 2.6, trace[-1][3]) < 0.8      # it did not go looking for it
