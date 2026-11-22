# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The BNO085 IMU (UART-RVC): the chip fuses gyro and accelerometer itself, no filter node needed.

    ros2 launch r2_imu_bno085 imu.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory("r2_imu_bno085"), "config", "imu.yaml")
    return LaunchDescription([
        Node(package="r2_imu_bno085", executable="bno085_node", name="imu",
             parameters=[config], output="screen"),
    ])
