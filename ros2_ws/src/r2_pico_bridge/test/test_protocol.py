import os

from r2_pico_bridge.protocol import cfg_line, parse
from r2_sensors.config import load_sensors

PACKAGE_YAML = os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml")


def test_cfg_line_from_the_package_sensors():
    line, names = cfg_line(load_sensors(PACKAGE_YAML))
    assert line == "CFG V:2 V:3 V:4 V:5 S:10:11 S:12:13 S:14:15\n"
    assert names == ["tof_front_left", "tof_front", "tof_front_right", "tof_floor",
                     "sonar_front_left", "sonar_front_right", "sonar_rear"]


def test_cfg_line_without_pico_sensors():
    lidar = {"lidar": {"type": "rplidar_c1", "port": "/dev/r2-lidar"}}
    assert cfg_line(lidar) == ("CFG\n", [])


def test_parse_heartbeat():
    assert parse("HB 12034 NNO") == ("hb", 12034, "NNO")
    assert parse("HB 5 -") == ("hb", 5, None)


def test_parse_readings():
    assert parse("R 0:420 3:-1") == ("r", [(0, 420), (3, -1)])
    assert parse("R 0:x") is None
    assert parse("R") is None


def test_parse_answers():
    assert parse("PICO r2_pico_sensors 0.1.0 proto 1") == ("hello", "0.1.0", 1)
    assert parse("CFG OK 7") == ("cfg_ok", 7)
    assert parse("CFG ERR pin 16 reserved") == ("cfg_err", "pin 16 reserved")
    assert parse("ERR unknown") == ("err", "unknown")


def test_parse_rubbish():
    for line in ("", "hello", "HB", "HB x NN", "HB 5 NX", "CFG OK x", "PICO other 1 proto 1"):
        assert parse(line) is None, line


def test_parse_heartbeat_with_no_sensors():
    assert parse("HB 5") == ("hb", 5, "")
