"""Start one camera node per entry in config/cameras.yaml.

    ros2 launch r2_camera cameras.launch.py
    ros2 launch r2_camera cameras.launch.py config:=/path/to/my_cameras.yaml
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def camera_nodes(context):
    path = LaunchConfiguration("config").perform(context)
    with open(path, encoding="utf-8") as f:
        cameras = yaml.safe_load(f) or {}
    nodes = []
    for name, params in cameras.items():
        params = dict(params or {})
        if "source" in params:
            params["source"] = str(params["source"])   # `source: 0` in YAML is an int
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
