# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math
import os
import re

import pytest

from r2_sensors.config import (SensorConfigError, angle_bounds, lidar_name, load_sensors,
                               parse_sensors, transforms)


def VL(name, extra):
    """One valid VL53L0X at x 0.2, y 0.07, z 0.25, plus extra lines."""
    lines = f"{name}:\n  type: vl53l0x\n  x: 0.2\n  y: 0.07\n  z: 0.25\n  pico: {{xshut: 2}}\n"
    return lines + "".join(f"  {line}\n" for line in extra.splitlines() if line)


LIDAR_200 = "lidar:\n  type: rplidar_c1\n  port: /dev/r2-lidar\n  x: 0.17\n  y: 0\n  z: 0.11\n"


def test_defaults_come_from_the_type():
    s = parse_sensors("tof_front:\n  type: vl53l0x\n  x: 0.2\n  y: 0\n  z: 0.25\n  pico: {xshut: 2}\n")
    assert s["tof_front"]["fov_deg"] == 25 and s["tof_front"]["range_max"] == 1.2
    assert s["tof_front"]["range_min"] == 0.03
    assert s["tof_front"]["yaw_deg"] == 0 and s["tof_front"]["pitch_deg"] == 0
    assert s["tof_front"]["stop_distance"] == 0


def test_order_is_kept():
    text = VL("b", "") + "a:\n  type: hcsr04\n  x: 0\n  y: 0\n  z: 0.3\n  pico: {trig: 3, echo: 4}\n"
    assert list(parse_sensors(text)) == ["b", "a"]


def test_no_sensors():
    assert parse_sensors("") == {}


@pytest.mark.parametrize("text,needle", [
    ("a: [1", "YAML"),
    ("x:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  pico: {xshut: 2}\n"
     "x:\n  type: hcsr04\n  x: 0\n  y: 0\n  z: 0\n  pico: {trig: 3, echo: 4}\n", "x: duplicated"),
    ("Bad-Name:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  pico: {xshut: 2}\n", "Bad-Name: name"),
    ("t:\n  type: laser\n  x: 0\n  y: 0\n  z: 0\n", "t: type"),
    ("t:\n  type: vl53l0x\n  y: 0\n  z: 0\n  pico: {xshut: 2}\n", "t: x"),
    ("t:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  fov_deg: 0\n  pico: {xshut: 2}\n", "t: fov_deg"),
    ("t:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  stop_distance: 2\n  pico: {xshut: 2}\n", "t: stop_distance"),
    ("t:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n", "t: pico"),
    ("t:\n  type: hcsr04\n  x: 0\n  y: 0\n  z: 0\n  pico: {trig: 3, echo: 3}\n", "t: pico"),
    ("a:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  pico: {xshut: 2}\n"
     "b:\n  type: hcsr04\n  x: 0\n  y: 0\n  z: 0\n  pico: {trig: 2, echo: 4}\n", "b: pico pin 2"),
    ("t:\n  type: vl53l0x\n  x: 0\n  y: 0\n  z: 0\n  pico: {xshut: 29}\n", "t: pico"),
    ("l1:\n  type: rplidar_c1\n  port: /dev/a\n  x: 0\n  y: 0\n  z: 0\n"
     "l2:\n  type: rplidar_c1\n  port: /dev/b\n  x: 0\n  y: 0\n  z: 0\n", "one lidar"),
    ("- a\n- b\n", "sensors"),
    ("t:\n  type: [vl53l0x]\n  x: 0\n  y: 0\n  z: 0\n", "t: type"),
    ("[a]: 1\n", "name"),
    ("t:\n  type: vl53l0x\n  ? [x]\n  : 1\n", "plain text"),
    ("l:\n  type: rplidar_c1\n  port: \"<img src=x onerror=alert(1)>\"\n  x: 0\n  y: 0\n  z: 0\n", "l: port"),
])

def test_bad_files_say_what_is_wrong(text, needle):
    with pytest.raises(SensorConfigError, match=re.escape(needle)):
        parse_sensors(text)


def test_reloader_survives_any_broken_file(tmp_path):
    from r2_sensors.config import Reloader
    p = tmp_path / "sensors.yaml"
    p.write_text("t:\n  type: [vl53l0x]\n  x: 0\n  y: 0\n  z: 0\n", encoding="utf-8")
    r = Reloader(lambda: str(p))
    assert r.poll() is None and r.error


def test_yaw_left_is_positive():
    (_, _, q), = transforms(parse_sensors(VL("a", "yaw_deg: 90")))
    assert q == pytest.approx((0, 0, 0.70711, 0.70711), abs=1e-4)


def test_pitch_down_is_positive():
    (_, _, q), = transforms(parse_sensors(VL("a", "pitch_deg: 90")))
    assert q == pytest.approx((0, 0.70711, 0, 0.70711), abs=1e-4)


def test_frame_and_position():
    (child, xyz, _), = transforms(parse_sensors(VL("tof_front", "")))
    assert child == "tof_front_link" and xyz == (0.2, 0.07, 0.25)


def test_lidar_bounds():
    s = parse_sensors(LIDAR_200)
    assert lidar_name(s) == "lidar"
    assert angle_bounds(s["lidar"]) == pytest.approx((-math.radians(100), math.radians(100)))


def test_no_lidar():
    assert lidar_name(parse_sensors(VL("a", ""))) is None


def test_package_default_is_valid():
    path = os.path.join(os.path.dirname(__file__), "..", "config", "sensors.yaml")
    assert len(load_sensors(path)) == 8
