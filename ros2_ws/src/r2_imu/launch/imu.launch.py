# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""MPU6050 plus a Madgwick filter that turns rotation + gravity into an orientation.

    ros2 launch r2_imu imu.launch.py

/imu/data_raw (our node) -> imu_filter_madgwick -> /imu/data (with orientation).
No magnetometer: indoors, next to the foot motors and batteries, a compass lies.
Heading drifts slowly; the lidar corrects it later (robot_localization).
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory("r2_imu"), "config", "imu.yaml")
    return LaunchDescription([
        Node(package="r2_imu", executable="imu_node", name="imu",
             parameters=[config], output="screen"),
        Node(package="imu_filter_madgwick", executable="imu_filter_madgwick_node",
             name="imu_filter", output="screen",
             parameters=[{"use_mag": False, "publish_tf": False, "world_frame": "enu"}]),
    ])
