# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Start one face detector per camera.

    ros2 launch r2_vision face_detectors.launch.py                  (cameras from r2_camera's config)
    ros2 launch r2_vision face_detectors.launch.py cameras:=front,rear
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from r2_camera.config import config_path, load_cameras
from r2_vision.remote_faces import faces_url


def detector_nodes(context):
    path = os.path.join(get_package_share_directory("r2_camera"), "config", "cameras.yaml")
    config = load_cameras(config_path(path))
    names = LaunchConfiguration("cameras").perform(context).strip()
    if names:
        cameras = [n.strip() for n in names.split(",") if n.strip()]
    else:
        cameras = list(config)
    nodes = []
    for name in cameras:
        params = config.get(name, {})
        if params.get("detect") == "camera":
            # The camera finds the faces itself: only pass them on (and turn them like the picture)
            nodes.append(Node(
                package="r2_vision",
                executable="remote_faces",
                name="face_detector",
                namespace=f"cameras/{name}",
                parameters=[{"url": params.get("faces_url") or faces_url(str(params.get("source", ""))),
                             "rotate": int(params.get("rotate", 0)),
                             "flip": str(params.get("flip", "none"))}],
                output="screen",
            ))
        else:
            nodes.append(Node(
                package="r2_vision",
                executable="face_detector",
                name="face_detector",
                namespace=f"cameras/{name}",
                parameters=[{"detect_width": int(LaunchConfiguration("detect_width").perform(context))}],
                output="screen",
            ))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("cameras", default_value="",
                              description="Comma-separated camera names; empty = all in r2_camera's config"),
        DeclareLaunchArgument("detect_width", default_value="320"),
        OpaqueFunction(function=detector_nodes),
    ])
