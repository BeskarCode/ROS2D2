# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Odometry on the droid without wheel encoders (see odometry.py): what really went to the Mega
plus the IMU's heading. The simulator publishes its own /odom: this node runs only on the droid.

  in   /mega/tx    std_msgs/String     every line the Mega bridge wrote (ROS:FOOT:<drive>,<turn>)
  in   /imu/data   sensor_msgs/Imu     Madgwick orientation (r2_imu imu.launch.py), optional
  out  /odom       nav_msgs/Odometry   20 Hz, frame odom -> base_link
  out  /tf         odom -> base_link

Parameters: drive_units_per_mps, turn_units_per_radps (the same calibration as the Mega bridge;
they are read from the running mega_bridge every 10 s when it is there).

    ros2 run r2_nav dead_reckoning
"""

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

from r2_nav.odometry import DeadReckoning, parse_foot, yaw_of

import math


class DeadReckoningNode(Node):
    def __init__(self):
        super().__init__("dead_reckoning")
        drive = self.declare_parameter("drive_units_per_mps", 50.0).value
        turn = self.declare_parameter("turn_units_per_radps", 30.0).value
        self.dr = DeadReckoning(drive, turn)
        self.pub_odom = self.create_publisher(Odometry, "/odom", 10)
        self.pub_tf = self.create_publisher(TFMessage, "/tf", 10)
        self.create_subscription(String, "/mega/tx", self._on_tx, 50)
        self.create_subscription(Imu, "/imu/data", self._on_imu, qos_profile_sensor_data)
        self.bridge_params = None
        try:
            from rclpy.parameter_client import AsyncParameterClient
            self.bridge_params = AsyncParameterClient(self, "mega_bridge")
        except ImportError:
            pass
        self.create_timer(10.0, self._read_calibration)
        self.create_timer(0.05, self._tick)
        self.get_logger().info("dead reckoning ready: /mega/tx + /imu/data -> /odom")

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_tx(self, m):
        foot = parse_foot(m.data)
        if foot is not None:
            self.dr.on_foot(self._now(), *foot)

    def _on_imu(self, m):
        q = m.orientation
        if q.x == q.y == q.z == q.w == 0:
            return                                    # raw IMU without an orientation
        self.dr.on_imu(self._now(), yaw_of(q.x, q.y, q.z, q.w))

    def _read_calibration(self):
        """The bridge's own calibration (foot_calibrate sets it there)."""
        if self.bridge_params is None or not self.bridge_params.services_are_ready():
            return
        fut = self.bridge_params.get_parameters(["drive_units_per_mps", "turn_units_per_radps"])

        def done(f):
            try:
                vals = [p.double_value for p in f.result().values]
            except Exception:                         # noqa: BLE001 - the bridge went away: keep ours
                return
            if len(vals) == 2 and all(v > 0 for v in vals):
                self.dr.drive_per_mps, self.dr.turn_per_radps = vals
        fut.add_done_callback(done)

    def _tick(self):
        x, y, th, v, w = self.dr.step(self._now())
        stamp = self.get_clock().now().to_msg()
        qz, qw = math.sin(th / 2), math.cos(th / 2)
        o = Odometry()
        o.header.stamp, o.header.frame_id, o.child_frame_id = stamp, "odom", "base_link"
        o.pose.pose.position.x, o.pose.pose.position.y = x, y
        o.pose.pose.orientation.z, o.pose.pose.orientation.w = qz, qw
        o.twist.twist.linear.x, o.twist.twist.angular.z = v, w
        self.pub_odom.publish(o)
        t = TransformStamped()
        t.header.stamp, t.header.frame_id, t.child_frame_id = stamp, "odom", "base_link"
        t.transform.translation.x, t.transform.translation.y = x, y
        t.transform.rotation.z, t.transform.rotation.w = qz, qw
        self.pub_tf.publish(TFMessage(transforms=[t]))


def main():
    rclpy.init()
    node = DeadReckoningNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
