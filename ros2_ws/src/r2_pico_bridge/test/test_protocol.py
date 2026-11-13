# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_pico_bridge.protocol import cfg_line, parse
from r2_sensors.config import load_sensors

PACKAGE_YAML = os.path.join(os.path.dirname(__file__), "..", "..", "r2_sensors", "config", "sensors.yaml")


def test_cfg_line_from_the_package_sensors():
    line, names = cfg_line(load_sensors(PACKAGE_YAML))
    assert line == "CFG V:2 V:3 V:4 V:5 S:10:11 S:12:13 S:14:15 S:18:19 S:20:21\n"
    assert names == ["tof_front_left", "tof_front", "tof_front_right", "tof_floor",
                     "sonar_front_left", "sonar_front_right", "sonar_rear", "sonar_left", "sonar_right"]


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
    assert parse("PICO r2_pico_sensors 0.1.0 proto 1") == ("hello", "0.1.0", 1, None)
    assert parse("PICO r2_pico_sensors 0.2.0 proto 2 commit 265a841") == ("hello", "0.2.0", 2, "265a841")
    assert parse("PICO r2_pico_sensors 0.2.0 proto 2 commit 265a841-dirty") == ("hello", "0.2.0", 2, "265a841-dirty")
    assert parse("TM OK") == ("tm_ok",)
    assert parse("CFG OK 7") == ("cfg_ok", 7)
    assert parse("CFG ERR pin 16 reserved") == ("cfg_err", "pin 16 reserved")
    assert parse("ERR unknown") == ("err", "unknown")


def test_parse_rubbish():
    for line in ("", "hello", "HB", "HB x NN", "HB 5 NX", "CFG OK x", "PICO other 1 proto 1"):
        assert parse(line) is None, line


def test_parse_heartbeat_with_no_sensors():
    assert parse("HB 5") == ("hb", 5, "")


def test_parse_telemetry():
    assert parse("T c0=12 c1=48 bus=51 disp=46 wait=37 temp=312 up=3600 rps=20,20,0") == ("tm", {
        "c0": 12, "c1": 48, "bus": 51, "disp": 46, "wait_ms": 37, "temp_c": 31.2, "up_s": 3600,
        "rps": [20, 20, 0]})
    assert parse("T c0=1 c1=2 bus=3 disp=0 wait=0 temp=-5 up=7 rps=")[1]["rps"] == []
    assert parse("T c0=1 c1=2 bus=3 disp=0 wait=0 temp=-5 up=7 rps=")[1]["temp_c"] == -0.5
    assert parse("T c0=x c1=2 bus=3 disp=0 wait=0 temp=1 up=7 rps=") is None
    assert parse("T c0=1 c1=2") is None


def test_parse_acks_of_the_board_settings():
    assert parse("UI OK") == ("ack", "UI", True, None)
    assert parse("UI ERR bad t") == ("ack", "UI", False, "bad t")
    assert parse("DISP OK") == ("ack", "DISP", True, None)
    assert parse("ID ERR bad connector") == ("ack", "ID", False, "bad connector")
    assert parse("XX OK") is None


def test_parse_what_the_display_shows():
    for s in ("off", "logo", "all", "VL1", "US5"):
        assert parse(f"DS {s}") == ("ds", s)
    assert parse("DS VL9") is None and parse("DS") is None


def test_parse_led_levels_of_the_mirror():
    assert parse("LED 100010000") == ("led", "100010000")
    assert parse("LED 10001") is None
    assert parse("LED 10001000x") is None
    assert parse("LED 1000100001") is None


def test_parse_the_display_picture_of_the_mirror():
    import base64
    picture = bytes(range(256)) * 4
    assert parse("FB " + base64.b64encode(picture).decode()) == ("fb", picture)
    assert parse("FB off") == ("fb", None)
    assert parse("FB " + base64.b64encode(bytes(1000)).decode()) is None     # not 1024 bytes
    assert parse("FB @@@") is None
    assert parse("FB " + base64.b64encode(picture).decode()[:-8]) is None    # cut short by the USB


def test_parse_button_presses_of_the_mirror():
    assert parse("BTN short") == ("btn", "short")
    assert parse("BTN long") == ("btn", "long")
    assert parse("BTN x") is None


def test_parse_acks_of_the_mirror():
    assert parse("MIR OK") == ("ack", "MIR", True, None)
    assert parse("PRESS OK") == ("ack", "PRESS", True, None)
    assert parse("PRESS ERR bad press") == ("ack", "PRESS", False, "bad press")
