"""The whole dome tracker demo: cameras -> face detectors -> dome tracker -> Mega bridge,
plus the sensors (their poses from sensors.yaml, and the lidar).

    ros2 launch r2_bringup dome_tracker.launch.py
    ros2 launch r2_bringup dome_tracker.launch.py port:=/dev/ttyACM0
    ros2 launch r2_bringup dome_tracker.launch.py mega:=false   # no Mega plugged in
    ros2 launch r2_bringup dome_tracker.launch.py lidar:=sim    # pretend lidar (none plugged in yet)

Web console (camera, faces, 3D dome, camera and sensor setup) on http://<pi>:8080/ unless web:=false.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def share(pkg, *path):
    return os.path.join(get_package_share_directory(pkg), *path)


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("port", default_value="/dev/r2-mega", description="Mega serial port"),
        DeclareLaunchArgument("mega", default_value="true", description="Start the Mega bridge"),
        DeclareLaunchArgument("web", default_value="true", description="Start the web console"),
        DeclareLaunchArgument("lidar", default_value="auto", choices=["auto", "sim", "off"],
                              description="auto: the real lidar if plugged in; sim: a pretend one; off"),

        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            share("r2_camera", "launch", "cameras.launch.py"))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            share("r2_vision", "launch", "face_detectors.launch.py"))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            share("r2_sensors", "launch", "sensors.launch.py")),
            launch_arguments={"lidar": LaunchConfiguration("lidar")}.items()),
        Node(
            package="r2_dome_tracker",
            executable="dome_tracker",
            name="dome_tracker",
            parameters=[
                share("r2_dome_tracker", "config", "dome_tracker.yaml"),
                # No Mega: the real dome cannot turn, so close the loop in simulation
                {"simulate": ParameterValue(PythonExpression(
                    ["'", LaunchConfiguration("mega"), "'.lower() != 'true'"]), value_type=bool)},
            ],
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
