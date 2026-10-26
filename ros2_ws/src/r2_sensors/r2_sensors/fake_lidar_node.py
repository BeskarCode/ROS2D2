"""A pretend lidar until the RPLIDAR C1 arrives: /scan_raw, a full turn every 0.1 s, of a
small room with a chair leg (r2_sensors.scan), seen from where sensors.yaml puts the lidar.
scan_crop then cuts it to what the droid does not hide, as with the real one.

    ros2 run r2_sensors fake_lidar
"""

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from r2_sensors.config import Reloader, config_path, lidar_name
from r2_sensors.scan import fake_ranges
from r2_sensors.sensor_tf_node import default_config

STEP = math.radians(0.5)
RAYS = int(round(2 * math.pi / STEP))


class FakeLidar(Node):
    def __init__(self):
        super().__init__("fake_lidar")
        default = self.declare_parameter("config", default_config()).value
        self.reloader = Reloader(lambda: config_path(default))
        self.pub = self.create_publisher(LaserScan, "scan_raw", 10)
        self.angles = [-math.pi + i * STEP for i in range(RAYS)]
        self.create_timer(1.0, self.reloader.poll)
        self.create_timer(0.1, self.publish)
        self.reloader.poll()

    def publish(self):
        name = lidar_name(self.reloader.sensors)
        s = self.reloader.sensors[name] if name else {"x": 0.0, "y": 0.0, "yaw_deg": 0.0,
                                                       "range_min": 0.05, "range_max": 12.0}
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f"{name or 'lidar'}_link"
        msg.angle_min = self.angles[0]
        msg.angle_max = self.angles[-1]
        msg.angle_increment = STEP
        msg.scan_time = 0.1
        msg.time_increment = 0.1 / RAYS
        msg.range_min = s["range_min"]
        msg.range_max = s["range_max"]
        msg.ranges = fake_ranges((s["x"], s["y"]), math.radians(s["yaw_deg"]), self.angles, s["range_max"])
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FakeLidar()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
