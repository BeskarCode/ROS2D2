# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigator driving the simulated R2 round the simulated room, without ROS (closed_loop.py):
the same checks as docker/nav_bench.sh, deterministic and in seconds."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
world_mod = pytest.importorskip("r2_sim.world")
pytest.importorskip("r2_shadow_bridge.protocol")
from closed_loop import drive  # noqa: E402
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
