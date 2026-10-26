"""The navigator alone (the simulation and the main launch include it).

    ros2 launch r2_nav nav.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_nav"), "config", "nav.yaml")
    return LaunchDescription([
        # nav_config, not config: a parent launch's own "config" argument would leak into it
        DeclareLaunchArgument("nav_config", default_value=default,
                              description="nav.yaml (the one in ~/.config/ros2d2 wins if it exists)"),
        Node(package="r2_nav", executable="navigator", name="navigator",
             parameters=[{"config": LaunchConfiguration("nav_config")}], output="screen"),
    ])
