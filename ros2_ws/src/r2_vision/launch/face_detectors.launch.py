"""Start one face detector per camera.

    ros2 launch r2_vision face_detectors.launch.py                  (cameras from r2_camera's config)
    ros2 launch r2_vision face_detectors.launch.py cameras:=front,rear
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def detector_nodes(context):
    names = LaunchConfiguration("cameras").perform(context).strip()
    if names:
        cameras = [n.strip() for n in names.split(",") if n.strip()]
    else:
        path = os.path.join(get_package_share_directory("r2_camera"), "config", "cameras.yaml")
        with open(path, encoding="utf-8") as f:
            cameras = list((yaml.safe_load(f) or {}).keys())
    return [
        Node(
            package="r2_vision",
            executable="face_detector",
            name="face_detector",
            namespace=f"cameras/{name}",
            parameters=[{"detect_width": int(LaunchConfiguration("detect_width").perform(context))}],
            output="screen",
        )
        for name in cameras
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("cameras", default_value="",
                              description="Comma-separated camera names; empty = all in r2_camera's config"),
        DeclareLaunchArgument("detect_width", default_value="320"),
        OpaqueFunction(function=detector_nodes),
    ])
