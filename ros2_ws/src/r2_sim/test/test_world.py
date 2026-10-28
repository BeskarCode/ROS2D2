# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import json
import math
import os

import pytest

from r2_sim.world import SensorSim, World, blocked_move, parse_foot, step_pose
from r2_sensors.config import load_sensors

SENSORS = load_sensors(os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml"))
ORIGIN = (0.0, 0.0, 0.0)


def test_cast_to_the_wall():
    w = World.empty()
    assert w.cast(0.17, 0.0, 0.0, 12.0, lambda d: 0.11) == pytest.approx(2.83)
    assert w.cast(0.17, 0.0, 0.0, 2.0, lambda d: 0.11) is None


def test_low_box_under_the_lidar():
    w = World.empty()
    w.apply({"op": "add", "kind": "low", "x": 1.5, "y": 0.0})        # 30 x 30 cm, 10 cm high
    sim = SensorSim(seed=1)
    _, inc, ranges = sim.scan(w, ORIGIN, SENSORS["lidar"])
    ahead = ranges[round(math.pi / inc)]                               # ray 0 of a scan from -pi
    assert ahead == pytest.approx(2.83, abs=0.02)                      # the wall: the box is too low
    s = dict(SENSORS["sonar_front_left"], yaw_deg=0.0, y=0.0)
    assert sim.range_of(w, ORIGIN, s) == pytest.approx(1.35 - 0.215, abs=0.03)
    w2 = World.empty()
    w2.apply({"op": "add", "kind": "low", "x": 0.7, "y": 0.0})
    assert sim.range_of(w2, ORIGIN, s) is None or sim.range_of(w2, ORIGIN, s) > 1.0   # close: the beam passes over


def test_tof_sees_a_post():
    w = World.empty()
    w.apply({"op": "add", "kind": "post", "x": 0.5, "y": 0.0})
    assert SensorSim(seed=1).range_of(w, ORIGIN, SENSORS["tof_front"]) == pytest.approx(0.245, abs=0.01)


def test_floor_sensor_reads_the_floor():
    d = SensorSim(seed=1).range_of(World.empty(), ORIGIN, SENSORS["tof_floor"])
    assert d == pytest.approx(0.28 / math.sin(math.radians(55)), abs=0.01)


def test_noise_is_repeatable_and_switchable():
    w = World.default()
    w.noise = True
    a = [SensorSim(seed=7).range_of(w, ORIGIN, SENSORS["sonar_front_left"]) for _ in range(1)]
    b = [SensorSim(seed=7).range_of(w, ORIGIN, SENSORS["sonar_front_left"]) for _ in range(1)]
    assert a == b
    w.noise = False
    s = SensorSim(seed=3)
    assert len({s.range_of(w, ORIGIN, SENSORS["tof_front"]) for _ in range(5)}) == 1


def test_parse_foot():
    assert parse_foot("ROS:FOOT:20,-5") == (20, -5)
    assert parse_foot("(not sent) ROS:FOOT:20,-5") is None
    assert parse_foot("MD:1") is None


def test_step_pose():
    x, y, th = step_pose((0.0, 0.0, 0.0), 0.4, 0.0, 0.5)
    assert (x, y, th) == pytest.approx((0.2, 0.0, 0.0))
    assert step_pose((0.0, 0.0, 0.0), 0.0, 1.0, 0.5)[2] == pytest.approx(0.5)


def test_world_edits():
    w = World.default()
    n = len(w.obstacles)
    oid = w.obstacles[0]["id"]
    assert w.apply({"op": "remove", "id": oid}) is None and len(w.obstacles) == n - 1
    assert w.apply({"op": "move", "id": w.obstacles[0]["id"], "x": 1.0, "y": 1.0}) is None
    assert w.obstacles[0]["x"] == 1.0
    assert "kind" in w.apply({"op": "add", "kind": "fly", "x": 0, "y": 0})
    assert "op" in w.apply({"op": "teleport"})
    assert w.apply({"op": "place", "x": 1.0, "y": -1.0, "th": 0.5}) is None and w.pose == [1.0, -1.0, 0.5]
    w.apply({"op": "reset"})
    assert len(w.obstacles) == n


def test_json_round_trip():
    w = World.default()
    w2 = World.from_json(w.to_json())
    assert json.loads(w2.to_json()) == json.loads(w.to_json())


def test_blocked_move():
    w = World.empty()
    w.apply({"op": "add", "kind": "box", "x": 1.0, "y": 0.0})
    assert blocked_move(w, (1.0, 0.0, 0.0))
    assert blocked_move(w, (2.9, 0.0, 0.0))                           # in the wall
    assert not blocked_move(w, (-1.0, 0.0, 0.0))


def test_box_corners_are_round():
    # 0.35 m from a box corner, diagonally: R2's 0.30 m footprint does not touch it
    w = World.empty()
    w.apply({"op": "add", "kind": "box", "x": 0.2, "y": 0.0, "w": 0.8, "h": 0.5})
    assert not blocked_move(w, (0.84, -0.50, 0.0))
    assert blocked_move(w, (0.75, -0.40, 0.0))
