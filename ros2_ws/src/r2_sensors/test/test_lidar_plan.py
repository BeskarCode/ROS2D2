# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_sensors.lidar_plan import lidar_plan


def test_sim_is_the_pretend_lidar_whatever_is_plugged_in():
    assert lidar_plan("sim", True, True) == ("fake", True)
    assert lidar_plan("sim", False, False) == ("fake", True)


def test_off_starts_nothing():
    assert lidar_plan("off", True, True) == (None, False)
    assert lidar_plan("off", True, False) == (None, False)


def test_with_the_service_the_launch_only_crops_even_with_no_lidar_yet():
    # the service brings the driver up when the lidar is plugged in; /scan must be ready for it
    assert lidar_plan("auto", True, True) == (None, True)
    assert lidar_plan("auto", False, True) == (None, True)


def test_without_the_service_the_launch_starts_the_driver_if_plugged_in():
    assert lidar_plan("auto", True, False) == ("sllidar", True)
    assert lidar_plan("auto", False, False) == (None, False)


def test_driver_params_from_the_lidar_block():
    from r2_sensors.config import parse_sensors
    from r2_sensors.lidar_plan import driver_params
    s = parse_sensors("front_lidar:\n  type: rplidar_c1\n  port: /dev/ttyUSB3\n  x: 0.17\n  y: 0\n  z: 0.11\n"
                      "  scan_mode: DenseBoost\n  inverted: true\n")
    assert driver_params(s) == {"serial_port": "/dev/ttyUSB3", "serial_baudrate": 460800,
                                "frame_id": "front_lidar_link", "scan_mode": "DenseBoost", "inverted": True,
                                "angle_compensate": True}


def test_driver_params_default_on_broken_file():
    from r2_sensors.lidar_plan import driver_params
    assert driver_params({}) == {"serial_port": "/dev/r2-lidar", "serial_baudrate": 460800,
                                 "frame_id": "lidar_link", "scan_mode": "Standard", "inverted": False,
                                 "angle_compensate": True}
