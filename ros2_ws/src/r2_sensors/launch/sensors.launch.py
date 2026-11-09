# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The droid's sensors: their poses on /tf_static from sensors.yaml, and the lidar.

    ros2 launch r2_sensors sensors.launch.py                # lidar:=auto
    ros2 launch r2_sensors sensors.launch.py lidar:=sim     # pretend lidar (none plugged in yet)
    ros2 launch r2_sensors sensors.launch.py lidar:=off

sensors_config:=/path/sensors.yaml uses another file (not "config": a parent launch's own
config argument, like the cameras' one, would leak into it).

lidar:=auto starts the RPLIDAR C1 driver (sllidar_ros2) when its port (from sensors.yaml,
/dev/r2-lidar by default) exists, and nothing otherwise. With r2d2-lidar.service installed the
driver is that service's (it follows the lidar being plugged in and out, see lidar_plan.py) and
this launch only runs scan_crop. Either lidar publishes /scan_raw; scan_crop turns it into /scan
without the angles the droid hides.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from r2_sensors.config import config_path, lidar_name, load_sensors
from r2_sensors.lidar_plan import SERVICE_FILE, lidar_plan


def lidar_port(config):
    """(name, port) of the lidar in sensors.yaml; a broken file must not stop the droid's launch."""
    try:
        sensors = load_sensors(config_path(config))
    except Exception as e:     # noqa: BLE001
        print(f"[sensors.launch] sensors.yaml: {e}")
        sensors = {}
    name = lidar_name(sensors)
    return name, sensors[name]["port"] if name else "/dev/r2-lidar"


def sllidar_node(name, port):
    """The RPLIDAR C1 driver, publishing /scan_raw (also used by lidar_driver.launch.py)."""
    return Node(
        package="sllidar_ros2",
        executable="sllidar_node",
        name="sllidar_node",
        parameters=[{"serial_port": port, "serial_baudrate": 460800,
                     "frame_id": f"{name or 'lidar'}_link", "scan_mode": "Standard",
                     "angle_compensate": True}],
        remappings=[("scan", "scan_raw")],
        output="screen",
    )


def lidar_nodes(context):
    config = LaunchConfiguration("sensors_config").perform(context)
    mode = LaunchConfiguration("lidar").perform(context)
    params = [{"config": config}]
    name, port = lidar_port(config)
    driver, crop = lidar_plan(mode, os.path.exists(port), os.path.exists(SERVICE_FILE))
    nodes = []
    if driver == "fake":
        nodes.append(Node(package="r2_sensors", executable="fake_lidar", name="fake_lidar",
                          parameters=params, output="screen"))
    elif driver == "sllidar":
        nodes.append(sllidar_node(name, port))
    elif mode == "auto" and os.path.exists(SERVICE_FILE):
        print(f"[sensors.launch] the lidar driver runs in r2d2-lidar.service while {port} is plugged in")
    elif mode == "auto":
        print(f"[sensors.launch] no lidar at {port} (lidar:=sim to pretend one)")
    if crop:
        nodes.append(Node(package="r2_sensors", executable="scan_crop", name="scan_crop",
                          parameters=params, output="screen"))
    return nodes


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
