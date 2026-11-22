# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigator, the follow node and the wander node (Patrol and Free roam's head) (one drives per mode) (the simulation and the main launch include it),
and on the droid the dead reckoning that gives them /odom (the simulator brings its own).

    ros2 launch r2_nav nav.launch.py                       # droid
    ros2 launch r2_nav nav.launch.py dead_reckoning:=false # the simulation
"""

import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _has(package):
    try:
        get_package_share_directory(package)
        return True
    except PackageNotFoundError:
        return False


def generate_launch_description():
    default = os.path.join(get_package_share_directory("r2_nav"), "config", "nav.yaml")
    # laser odometry for the dead reckoning, when setup_r2_brain.sh could build it
    rf2o = [Node(package="rf2o_laser_odometry", executable="rf2o_laser_odometry_node", name="rf2o_laser_odometry",
                 output="screen", condition=IfCondition(LaunchConfiguration("dead_reckoning")),
                 parameters=[{"laser_scan_topic": "/scan", "odom_topic": "/odom_rf2o",
                              "publish_tf": False,           # odom -> base_link comes from the dead reckoning
                              "base_frame_id": "base_link", "odom_frame_id": "odom",
                              "init_pose_from_topic": "", "freq": 10.0}],
                 # rf2o logs every scan at INFO (and "Waiting for laser_scans" at WARN, 10 a second,
                 # with the lidar unplugged): that filled the journal and cost CPU on the Pi
                 arguments=["--ros-args", "--log-level", "rf2o_laser_odometry:=error"])] if _has("rf2o_laser_odometry") else []
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
        # the head of Patrol and Free roam (the navigator is their legs)
        Node(package="r2_nav", executable="wander", name="wander",
             parameters=[{"config": LaunchConfiguration("nav_config")}], output="screen"),
        Node(package="r2_nav", executable="dead_reckoning", name="dead_reckoning", output="screen",
             condition=IfCondition(LaunchConfiguration("dead_reckoning"))),
        *rf2o,
    ])
