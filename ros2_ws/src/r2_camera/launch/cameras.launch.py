# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Start one camera node per entry in config/cameras.yaml.

    ros2 launch r2_camera cameras.launch.py
    ros2 launch r2_camera cameras.launch.py config:=/path/to/my_cameras.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from r2_camera.config import config_path, load_cameras, node_params


def camera_nodes(context):
    cameras = load_cameras(config_path(LaunchConfiguration("config").perform(context)))
    if not cameras:
        print("[cameras.launch] no camera found (cameras.yaml is on auto and nothing is plugged in)")
    nodes = []
    for name, params in cameras.items():
        params = node_params(params)
        nodes.append(Node(
            package="r2_camera",
            executable="camera_node",
            name="camera",
            namespace=f"cameras/{name}",
            parameters=[params],
            output="screen",
        ))
    return nodes


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_camera"), "config", "cameras.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("config", default_value=default,
                              description="YAML file with one block per camera"),
        OpaqueFunction(function=camera_nodes),
    ])
