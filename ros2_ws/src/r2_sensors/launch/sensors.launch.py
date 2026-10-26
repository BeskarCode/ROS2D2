"""The droid's sensors: their poses on /tf_static from sensors.yaml, and the lidar.

    ros2 launch r2_sensors sensors.launch.py                # lidar:=auto
    ros2 launch r2_sensors sensors.launch.py lidar:=sim     # pretend lidar (none plugged in yet)
    ros2 launch r2_sensors sensors.launch.py lidar:=off

sensors_config:=/path/sensors.yaml uses another file (not "config": a parent launch's own
config argument, like the cameras' one, would leak into it).

lidar:=auto starts the RPLIDAR C1 driver (sllidar_ros2) when its port (from sensors.yaml,
/dev/r2-lidar by default) exists, and nothing otherwise. Either lidar publishes /scan_raw;
scan_crop turns it into /scan without the angles the droid hides.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from r2_sensors.config import config_path, lidar_name, load_sensors


def lidar_nodes(context):
    config = LaunchConfiguration("sensors_config").perform(context)
    mode = LaunchConfiguration("lidar").perform(context)
    params = [{"config": config}]
    try:
        sensors = load_sensors(config_path(config))
    except Exception as e:     # a broken file must not stop the whole droid launch  # noqa: BLE001
        print(f"[sensors.launch] sensors.yaml: {e}")
        sensors = {}
    name = lidar_name(sensors)
    port = sensors[name]["port"] if name else "/dev/r2-lidar"
    crop = Node(package="r2_sensors", executable="scan_crop", name="scan_crop",
                parameters=params, output="screen")
    if mode == "sim":
        return [Node(package="r2_sensors", executable="fake_lidar", name="fake_lidar",
                     parameters=params, output="screen"), crop]
    if mode == "auto" and os.path.exists(port):
        return [Node(
            package="sllidar_ros2",
            executable="sllidar_node",
            name="sllidar_node",
            parameters=[{"serial_port": port, "serial_baudrate": 460800,
                         "frame_id": f"{name or 'lidar'}_link", "scan_mode": "Standard",
                         "angle_compensate": True}],
            remappings=[("scan", "scan_raw")],
            output="screen",
        ), crop]
    if mode == "auto":
        print(f"[sensors.launch] no lidar at {port} (lidar:=sim to pretend one)")
    return []


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("sensors_config", default_value=default,
                              description="sensors.yaml (the one in ~/.config/ros2d2 wins if it exists)"),
        DeclareLaunchArgument("lidar", default_value="auto", choices=["auto", "sim", "off"],
                              description="auto: the real lidar if plugged in; sim: a pretend one; off"),
        Node(package="r2_sensors", executable="sensor_tf", name="sensor_tf",
             parameters=[{"config": LaunchConfiguration("sensors_config")}], output="screen"),
        OpaqueFunction(function=lidar_nodes),
    ])
