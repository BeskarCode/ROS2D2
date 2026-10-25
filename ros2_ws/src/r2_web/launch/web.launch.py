"""Web console: rosbridge (ws :9090), the page server (http :8080) and web_video_server
(http :8081), which sends the cameras' JPEG pictures to the browser as MJPEG without
re-encoding them: far lighter than passing them through rosbridge.

    ros2 launch r2_web web.launch.py
    then open http://<pi>:8080/
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    rosbridge = os.path.join(get_package_share_directory("rosbridge_server"),
                             "launch", "rosbridge_websocket_launch.xml")
    return LaunchDescription([
        DeclareLaunchArgument("http_port", default_value="8080"),
        DeclareLaunchArgument("ws_port", default_value="9090"),
        DeclareLaunchArgument("video_port", default_value="8081"),
        # Pass rosbridge its port explicitly: otherwise a parent launch's own "port"
        # argument (the Mega's /dev/r2-mega) leaks into it
        IncludeLaunchDescription(AnyLaunchDescriptionSource(rosbridge),
                                 launch_arguments={"port": LaunchConfiguration("ws_port")}.items()),
        Node(
            package="web_video_server",
            executable="web_video_server",
            name="web_video_server",
            parameters=[{"port": ParameterValue(LaunchConfiguration("video_port"), value_type=int)}],
            output="screen",
        ),
        Node(
            package="r2_web",
            executable="web_console",
            name="web_console",
            parameters=[{"port": ParameterValue(LaunchConfiguration("http_port"), value_type=int)}],
            output="screen",
        ),
    ])
