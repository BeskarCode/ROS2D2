"""The whole dome tracker demo: cameras -> face detectors -> dome tracker -> Mega bridge.

    ros2 launch r2_bringup dome_tracker.launch.py
    ros2 launch r2_bringup dome_tracker.launch.py port:=/dev/ttyACM0
    ros2 launch r2_bringup dome_tracker.launch.py mega:=false   # no Mega plugged in

Web console (camera, faces, 3D dome) on http://<pi>:8080/ unless web:=false.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def share(pkg, *path):
    return os.path.join(get_package_share_directory(pkg), *path)


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("port", default_value="/dev/r2-mega", description="Mega serial port"),
        DeclareLaunchArgument("mega", default_value="true", description="Start the Mega bridge"),
        DeclareLaunchArgument("web", default_value="true", description="Start the web console"),

        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            share("r2_camera", "launch", "cameras.launch.py"))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            share("r2_vision", "launch", "face_detectors.launch.py"))),
        Node(
            package="r2_dome_tracker",
            executable="dome_tracker",
            name="dome_tracker",
            parameters=[share("r2_dome_tracker", "config", "dome_tracker.yaml")],
            output="screen",
        ),
        Node(
            package="r2_shadow_bridge",
            executable="mega_bridge",
            name="mega_bridge",
            parameters=[{"port": LaunchConfiguration("port")}],
            output="screen",
            condition=IfCondition(LaunchConfiguration("mega")),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(share("r2_web", "launch", "web.launch.py")),
            condition=IfCondition(LaunchConfiguration("web"))),
    ])
