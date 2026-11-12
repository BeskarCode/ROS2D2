# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.lidar_api import lidar_needs_restart

BASE = "lidar:\n  type: rplidar_c1\n  port: /dev/r2-lidar\n  x: 0.17\n  y: 0\n  z: 0.11\n"


def test_restart_only_when_driver_settings_change():
    assert not lidar_needs_restart(BASE, BASE.replace("x: 0.17", "x: 0.18"))
    assert not lidar_needs_restart(BASE, BASE + "  motor: off\n  blind_sectors: [[100, 140]]\n")
    assert lidar_needs_restart(BASE, BASE + "  scan_mode: DenseBoost\n")
    assert lidar_needs_restart(BASE, BASE + "  inverted: true\n")
    assert not lidar_needs_restart(BASE, BASE + "  scan_mode: Standard\n")   # the default: same driver
    assert not lidar_needs_restart(BASE, "lidar: [broken")
    assert not lidar_needs_restart("lidar: [broken", BASE)


def test_restart_when_the_lidar_comes_or_goes():
    assert lidar_needs_restart("", BASE)
    assert lidar_needs_restart(BASE, "")
    assert not lidar_needs_restart("", "")
