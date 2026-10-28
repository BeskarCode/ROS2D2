# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Drive the feet at a fixed number of Sabertooth units to measure how fast that is.

The feet have no encoders, so the Mega bridge needs two numbers from the real droid:
drive_units_per_mps and turn_units_per_radps. With the droid on the floor and room
around it:

    ros2 run r2_shadow_bridge foot_calibrate --drive 20 --seconds 3   # measure metres
    ros2 run r2_shadow_bridge foot_calibrate --turn 15 --seconds 4    # count full turns

It needs the autonomous mode on (PS + L2 on the foot controller) and the Mega bridge
running; the stick stops it at any moment, as always. It goes through /foot/cmd_vel,
so the bridge's max_linear / max_angular and the Mega's own limits still apply.
"""

import argparse
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

from r2_shadow_bridge.protocol import calibration_factor, units_to_twist

BRIDGE = "/mega_bridge"
PARAMS = ["drive_units_per_mps", "turn_units_per_radps", "max_linear", "max_angular"]


def bridge_params(node):
    client = AsyncParameterClient(node, BRIDGE)
    if not client.wait_for_services(timeout_sec=10.0):
        sys.exit(f"{BRIDGE} is not running")
    future = client.get_parameters(PARAMS)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
    if future.result() is None:
        sys.exit(f"could not read the parameters of {BRIDGE}")
    return {name: v.double_value for name, v in zip(PARAMS, future.result().values)}


def wait_for_auto_mode(node, timeout=120.0):
    state = {"on": False}
    latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
    node.create_subscription(Bool, "/r2/auto_mode", lambda m: state.update(on=m.data), latched)
    print("Waiting for the autonomous mode: press PS + L2 on the foot controller...")
    end = time.monotonic() + timeout
    while not state["on"] and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.2)
    return state["on"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--drive", type=int, help="Sabertooth drive units (forward > 0)")
    what.add_argument("--turn", type=int, help="Sabertooth turn units")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--measured", type=float,
                    help="metres (or full turns) measured; asked for if not given")
    args = ap.parse_args(rclpy.utilities.remove_ros_args()[1:])

    rclpy.init()
    node = rclpy.create_node("foot_calibrate")
    p = bridge_params(node)
    turning = args.turn is not None
    units = args.turn if turning else args.drive
    linear, angular = units_to_twist(0 if turning else units, units if turning else 0,
                                     p["drive_units_per_mps"], p["turn_units_per_radps"])
    if abs(linear) > p["max_linear"] or abs(angular) > p["max_angular"]:
        sys.exit(f"{units} units is above the bridge's max_linear/max_angular "
                 f"({p['max_linear']} m/s, {p['max_angular']} rad/s): ask for fewer units")

    pub = node.create_publisher(Twist, "/foot/cmd_vel", 10)
    if not wait_for_auto_mode(node):
        sys.exit("the autonomous mode did not come on")

    print(f"{'Turning' if turning else 'Driving'} at {units} units for {args.seconds} s")
    msg = Twist()
    msg.linear.x, msg.angular.z = linear, angular
    end = time.monotonic() + args.seconds
    while time.monotonic() < end:
        pub.publish(msg)
        rclpy.spin_once(node, timeout_sec=1 / 15)
    pub.publish(Twist())          # stop; the bridge then sends a single ROS:FOOT:0,0
    rclpy.spin_once(node, timeout_sec=0.2)

    measured = args.measured
    if measured is None:
        measured = float(input("Full turns made: " if turning else "Metres covered: "))
    name = "turn_units_per_radps" if turning else "drive_units_per_mps"
    value = calibration_factor(units, measured, args.seconds, turning)
    print(f"{name} = {value:.1f}")
    print(f"  try it:   ros2 param set {BRIDGE} {name} {value:.1f}")
    print(f"  keep it:  add '{name}: {value:.1f}' to the bridge's parameters")
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
