# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Spins the lidar's motor as sensors.yaml says (lidar motor: always | with_modes | off).

  in   /r2/auto_mode   std_msgs/Bool     (latched)
  in   /r2/mode        std_msgs/String   (latched)
  in   /lidar/info     std_msgs/String   (latched; a new one = the driver restarted)
  out  /start_motor, /stop_motor         std_srvs/Empty, sllidar_ros2's services

    ros2 run r2_sensors lidar_motor
"""

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, String
from std_srvs.srv import Empty

from r2_sensors.config import Reloader, config_path, lidar_name
from r2_sensors.lidar_motor import MotorPolicy, mode_active
from r2_sensors.sensor_tf_node import default_config


class LidarMotor(Node):
    def __init__(self):
        super().__init__("lidar_motor")
        default = self.declare_parameter("config", default_config()).value
        self.reloader = Reloader(lambda: config_path(default))
        self.reloader.poll()
        self.auto_on, self.mode = False, None
        self.policy = MotorPolicy()
        self.pending = None             # an order the driver has not taken yet (it was not up)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        # react at once (not on the next 1 s tick): the C1 needs about 4 s to give its first scan
        self.create_subscription(Bool, "/r2/auto_mode", lambda m: (setattr(self, "auto_on", m.data), self.tick()), latched)
        self.create_subscription(String, "/r2/mode", lambda m: (setattr(self, "mode", m.data), self.tick()), latched)
        # the driver publishes /lidar/info each time it starts (spinning): give it the order again
        self.create_subscription(String, "/lidar/info", lambda _m: self.policy.driver_restarted(), latched)
        self.motor_clients = {o: self.create_client(Empty, f"/{o}_motor") for o in ("start", "stop")}
        self.create_timer(1.0, self.tick)

    def tick(self):
        self.reloader.poll()
        sensors = self.reloader.sensors
        name = lidar_name(sensors)
        if name is None:
            return
        order = self.policy.update(time.monotonic(), sensors[name].get("motor", "always"),
                                   mode_active(self.auto_on, self.mode)) or self.pending
        if order is None:
            return
        client = self.motor_clients[order]
        if not client.service_is_ready():
            self.pending = order        # the driver is not up: try again next second
            return
        self.pending = None
        client.call_async(Empty.Request())
        self.get_logger().info(f"lidar motor: {order}")


def main():
    rclpy.init()
    node = LidarMotor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
