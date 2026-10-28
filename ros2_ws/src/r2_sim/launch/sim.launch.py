# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The simulated droid: a room, pretend sensors, and a fake Mega on a pty with the REAL
Mega bridge talking to it (so the bridge is tested too). The navigator and the sensor poses
come from the main launch (sim:=true) or from their own launches.

    ros2 launch r2_sim sim.launch.py

socat makes two linked ptys: the bridge opens /tmp/r2sim-mega, the fake Mega the other end.
The web page's "Autonomous ON (PS + L2)" writes "button" into the fake Mega's FIFO.
"""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

BRIDGE_SIDE = "/tmp/r2sim-mega"
MEGA_SIDE = "/tmp/r2sim-mega-side"
MEGA_LOG = "/tmp/r2sim-mega.log"
MEGA_CTL = "/tmp/r2sim-mega-ctl"


def generate_launch_description():
    return LaunchDescription([
        ExecuteProcess(cmd=["socat", f"pty,raw,echo=0,link={BRIDGE_SIDE}", f"pty,raw,echo=0,link={MEGA_SIDE}"],
                       name="mega_pty", output="log"),
        TimerAction(period=1.0, actions=[
            ExecuteProcess(cmd=["ros2", "run", "r2_sim", "fake_mega", MEGA_SIDE, MEGA_LOG, MEGA_CTL],
                           name="fake_mega", output="log"),
        ]),
        TimerAction(period=2.0, actions=[
            Node(package="r2_shadow_bridge", executable="mega_bridge", name="mega_bridge",
                 parameters=[{"port": BRIDGE_SIDE, "open_wait": 0.5}], output="screen"),
        ]),
        Node(package="r2_sim", executable="sim_world", name="sim_world",
             parameters=[{"mega_ctl": MEGA_CTL}], output="screen"),
        # the room's lidar publishes /scan_raw; cut it like the real one
        Node(package="r2_sensors", executable="scan_crop", name="scan_crop", output="screen"),
    ])
