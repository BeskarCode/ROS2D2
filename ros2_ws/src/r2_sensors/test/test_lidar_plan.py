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
