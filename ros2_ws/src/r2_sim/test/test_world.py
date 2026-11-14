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
    assert SENSORS["tof_floor"]["pitch_deg"] == 40                   # sees low things ~0.5 m ahead
    d = SensorSim(seed=1).range_of(World.empty(), ORIGIN, SENSORS["tof_floor"])
    assert d == pytest.approx(0.28 / math.sin(math.radians(40)), abs=0.01)


def test_floor_sensor_sees_a_low_box():
    # the beam leaves at 0.28 m going down 40 deg: it meets the floor 0.53 m from the body
    # centre, so a 10 cm box whose face is 0.45 m ahead cuts it short (lidar and ToFs miss it)
    w = World.empty()
    w.apply({"op": "add", "kind": "low", "x": 0.45 + 0.15, "y": 0.0})        # 30 x 30 cm
    d = SensorSim(seed=1).range_of(w, ORIGIN, SENSORS["tof_floor"])
    assert d == pytest.approx((0.45 - 0.2) / math.cos(math.radians(40)), abs=0.01)
    w2 = World.empty()
    w2.apply({"op": "add", "kind": "low", "x": 0.7 + 0.15, "y": 0.0})         # beyond where it looks
    d2 = SensorSim(seed=1).range_of(w2, ORIGIN, SENSORS["tof_floor"])
    assert d2 == pytest.approx(0.28 / math.sin(math.radians(40)), abs=0.01)


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


def test_floor_sensor_cone_sees_a_low_box_a_little_to_the_side():
    # the VL53L0X's 25 deg cone, not one ray: a box 5 cm off the centre line is still seen (the cone is ~±7 cm wide where it meets the floor)
    w = World.empty()
    w.apply({"op": "add", "kind": "low", "x": 0.45 + 0.15, "y": 0.05 + 0.15})
    d = SensorSim(seed=1).range_of(w, ORIGIN, SENSORS["tof_floor"])
    assert d < 0.28 / math.sin(math.radians(40)) * 0.8


def test_marker_view_in_front():
    w = World.empty()
    w.apply({"op": "add", "kind": "post", "x": 1.5, "y": 0.0, "r": 0.15, "height": 1.7, "marker": True})
    v = w.marker_view(ORIGIN)
    assert v["seen"] and v["bearing"] == pytest.approx(0.0) and v["cx"] == pytest.approx(0.5)
    assert 0.03 < v["area"] < 0.12
    far = w.marker_view((-1.0, 0.0, 0.0))
    assert far["area"] < v["area"]                                     # further away: smaller
    left = w.marker_view((0.5, -0.5, 0.0))                             # the person is to its left
    assert left["bearing"] > 0 and left["cx"] < 0.5
    assert w.marker_view((0.0, 0.0, math.pi)) is None                  # looking the other way
    w.apply({"op": "marker", "id": 1, "on": False})
    assert w.marker_view(ORIGIN) is None                               # no shirt


def test_marker_hidden_behind_box():
    w = World.empty()
    w.apply({"op": "add", "kind": "post", "x": 2.0, "y": 0.0, "r": 0.15, "height": 1.7, "marker": True})
    w.apply({"op": "add", "kind": "box", "x": 1.0, "y": 0.0, "w": 0.5, "h": 0.5, "height": 1.3})
    assert w.marker_view(ORIGIN) is None
    w.apply({"op": "move", "id": 2, "x": 1.0, "y": 1.0})               # the box is no longer in the way
    assert w.marker_view(ORIGIN)["seen"]
    w.apply({"op": "move", "id": 2, "x": 1.0, "y": 0.0})
    w.apply({"op": "add", "kind": "low", "x": 1.0, "y": 0.0})
    w.apply({"op": "remove", "id": 2})
    assert w.marker_view(ORIGIN)["seen"]                               # a low box does not hide a shirt


# ---------- room presets ----------
from r2_sim.world import ROOMS  # noqa: E402


@pytest.mark.parametrize("name", sorted(ROOMS))
def test_every_preset_start_is_free(name):
    w = World.preset(name)
    assert not blocked_move(w, w.pose)
    assert w.obstacles, name


def test_presets_are_the_four_rooms_and_the_default():
    assert {"default", "living", "corridor", "rooms", "event"} <= set(ROOMS)


def test_room_op_loads_and_reset_returns_to_it():
    w = World.default()
    w.noise = False
    assert w.apply({"op": "room", "name": "corridor"}) is None
    assert w.room == World.preset("corridor").room
    assert w.noise is False                                       # kept
    start = list(w.pose)
    w.apply({"op": "add", "kind": "post", "x": 0.0, "y": 0.0})
    w.pose = [0.0, 0.0, 0.0]
    w.apply({"op": "reset"})
    assert w.pose == start
    assert len(w.obstacles) == len(World.preset("corridor").obstacles)


def test_room_op_unknown_name():
    err = World.default().apply({"op": "room", "name": "kitchen"})
    assert err and "corridor" in err


def test_wall_is_hit_at_lidar_height():
    w = World.empty()
    w.apply({"op": "add", "kind": "wall", "x": 1.0, "y": 0.0, "w": 0.1, "h": 2.0})
    assert w.cast(0.0, 0.0, 0.0, 5.0, lambda d: 0.245) == pytest.approx(0.95)
    assert blocked_move(w, (0.8, 0.0, 0.0))


def test_event_has_a_person_with_a_shirt():
    w = World.preset("event")
    assert any(o.get("marker") and o["kind"] == "post" and o["r"] >= 0.15 for o in w.obstacles)


def test_room_name_travels_in_json():
    w = World.preset("living")
    assert json.loads(w.to_json())["name"] == "living"
    assert World.from_json(w.to_json()).name == "living"


def test_sensors_to_publish_skips_off():
    from r2_sim.world import sensors_to_publish
    s = {"lidar": {"type": "rplidar_c1"}, "tof_front": {"type": "vl53l0x"}, "sonar_rear": {"type": "hcsr04"}}
    assert sorted(sensors_to_publish(s, {"lidar", "sonar_rear"})) == ["tof_front"]
    assert sorted(sensors_to_publish(s, set())) == ["lidar", "sonar_rear", "tof_front"]
