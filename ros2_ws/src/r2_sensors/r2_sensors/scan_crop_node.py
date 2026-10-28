# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/scan_raw -> /scan without the rays the droid's own body hides: the lidar sits on the
front foot and only sees ahead. The angle comes from the lidar's fov_deg in sensors.yaml
(our own node instead of laser_filters, which may not exist for every ROS release).

    ros2 run r2_sensors scan_crop
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from r2_sensors.config import Reloader, angle_bounds, config_path, lidar_name
from r2_sensors.scan import crop
from r2_sensors.sensor_tf_node import default_config


class ScanCrop(Node):
    def __init__(self):
        super().__init__("scan_crop")
        default = self.declare_parameter("config", default_config()).value
        self.reloader = Reloader(lambda: config_path(default))
        self.reloader.poll()
        self.create_timer(1.0, self.reloader.poll)
        self.warned = False
        self.pub = self.create_publisher(LaserScan, "scan", 10)
        self.create_subscription(LaserScan, "scan_raw", self.on_scan, qos_profile_sensor_data)

    def on_scan(self, msg):
        name = lidar_name(self.reloader.sensors)
        if name is None:
            if not self.warned:
                self.get_logger().warning("no lidar in sensors.yaml: /scan is not cut")
                self.warned = True
        else:
            lower, upper = angle_bounds(self.reloader.sensors[name])
            msg.ranges = crop(list(msg.ranges), msg.angle_min, msg.angle_increment, lower, upper)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ScanCrop()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
