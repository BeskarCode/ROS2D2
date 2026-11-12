# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Only the RPLIDAR C1 driver, for r2d2-lidar.service (udev starts it when the lidar is plugged in
and systemd stops it when it is unplugged). scan_crop stays in the droid's main launch.

    ros2 launch r2_sensors lidar_driver.launch.py
"""

import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration

# the lidar's port and driver node, the same as in sensors.launch.py
_spec = importlib.util.spec_from_file_location("sensors_launch", os.path.join(os.path.dirname(__file__), "sensors.launch.py"))
_sensors = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sensors)


def driver(context):
    return [_sensors.sllidar_node(_sensors.lidar_settings(LaunchConfiguration("sensors_config").perform(context)))]


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("sensors_config", default_value=default,
                              description="sensors.yaml (the one in ~/.config/ros2d2 wins if it exists)"),
        OpaqueFunction(function=driver),
    ])
