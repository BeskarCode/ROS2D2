# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_sensors.lidar_motor import MotorPolicy, mode_active


def test_with_modes_starts_on_activation_and_stops_after_5_s():
    p = MotorPolicy()
    assert p.update(0, "with_modes", False) == "stop"
    assert p.update(1, "with_modes", True) == "start"
    assert p.update(2, "with_modes", False) is None
    assert p.update(6.9, "with_modes", False) is None and p.update(7.1, "with_modes", False) == "stop"


def test_with_modes_a_quick_mode_change_keeps_it_spinning():
    p = MotorPolicy()
    assert p.update(0, "with_modes", True) == "start"
    assert p.update(1, "with_modes", False) is None
    assert p.update(3, "with_modes", True) is None          # back within 5 s: never stopped
    assert p.update(7, "with_modes", False) is None


def test_always_and_off_ignore_the_modes():
    p = MotorPolicy()
    assert p.update(0, "always", False) == "start" and p.update(1, "always", True) is None
    q = MotorPolicy()
    assert q.update(0, "off", True) == "stop" and q.update(1, "off", False) is None


def test_changing_the_policy_acts_at_once():
    p = MotorPolicy()
    assert p.update(0, "always", False) == "start"
    assert p.update(1, "off", False) == "stop"
    assert p.update(2, "always", False) == "start"


def test_mode_active():
    assert mode_active(True, "follow") and mode_active(True, "patrol") and mode_active(True, None)
    assert not mode_active(False, "goto") and not mode_active(True, "dome")
