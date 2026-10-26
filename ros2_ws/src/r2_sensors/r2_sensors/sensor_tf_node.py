"""Where each sensor sits on the droid, on /tf_static (base_link -> <name>_link), from
sensors.yaml. Saving the file from the web console moves them within a second.

    ros2 run r2_sensors sensor_tf
    ros2 run r2_sensors sensor_tf --ros-args -p config:=/path/to/sensors.yaml
"""

import os

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage

from r2_sensors.config import Reloader, config_path, transforms


def default_config():
    return os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")


class SensorTf(Node):
    def __init__(self):
        super().__init__("sensor_tf")
        default = self.declare_parameter("config", default_config()).value
        self.reloader = Reloader(lambda: config_path(default))
        # Our own latched /tf_static instead of tf2's StaticTransformBroadcaster, which keeps
        # every frame it ever sent: a sensor removed or renamed would stay in the message
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.pub = self.create_publisher(TFMessage, "/tf_static", latched)
        self.last_error = None
        self.poll()
        self.create_timer(1.0, self.poll)

    def poll(self):
        sensors = self.reloader.poll()
        if self.reloader.error and self.reloader.error != self.last_error:
            self.get_logger().error(f"sensors.yaml: {self.reloader.error} (keeping the last good one)")
        self.last_error = self.reloader.error
        if sensors is None:
            return
        now = self.get_clock().now().to_msg()
        msgs = []
        for child, (x, y, z), (qx, qy, qz, qw) in transforms(sensors):
            t = TransformStamped()
            t.header.stamp = now
            t.header.frame_id = "base_link"
            t.child_frame_id = child
            t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = x, y, z
            t.transform.rotation.x, t.transform.rotation.y = qx, qy
            t.transform.rotation.z, t.transform.rotation.w = qz, qw
            msgs.append(t)
        self.pub.publish(TFMessage(transforms=msgs))     # the whole list, even when empty
        self.get_logger().info(f"{len(msgs)} sensors from {self.reloader.path_fn()}")


def main():
    rclpy.init()
    node = SensorTf()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
