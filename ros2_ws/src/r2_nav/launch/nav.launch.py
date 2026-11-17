# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigator and the follow node (one drives per mode) (the simulation and the main launch include it),
and on the droid the dead reckoning that gives them /odom (the simulator brings its own).

    ros2 launch r2_nav nav.launch.py                       # droid
    ros2 launch r2_nav nav.launch.py dead_reckoning:=false # the simulation
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_nav"), "config", "nav.yaml")
    return LaunchDescription([
        # nav_config, not config: a parent launch's own "config" argument would leak into it
        DeclareLaunchArgument("nav_config", default_value=default,
                              description="nav.yaml (the one in ~/.config/ros2d2 wins if it exists)"),
        DeclareLaunchArgument("dead_reckoning", default_value="true",
                              description="true: /odom from what went to the Mega + the IMU (false in the simulation)"),
        Node(package="r2_nav", executable="navigator", name="navigator",
             parameters=[{"config": LaunchConfiguration("nav_config")}], output="screen"),
        Node(package="r2_nav", executable="follow", name="follow",
             parameters=[{"config": LaunchConfiguration("nav_config")}], output="screen"),
        Node(package="r2_nav", executable="dead_reckoning", name="dead_reckoning", output="screen",
             condition=IfCondition(LaunchConfiguration("dead_reckoning"))),
    ])
