"""The simulated room on ROS: R2 moves with what the Mega bridge really sends to the (fake)
Mega, and its pretend sensors publish on the same topics as the real ones.

  in   /mega/tx          std_msgs/String   lines sent to the Mega: ROS:FOOT:<drive>,<turn> moves R2
                                           (as the Mega does: each one lasts 0.3 s)
  in   /sim/world_cmd    std_msgs/String   JSON edits from the web page: add, move, remove, reset,
                                           place, noise, save, load, press (the fake Mega's buttons)
  out  /odom             nav_msgs/Odometry and TF odom -> base_link
  out  /scan_raw         sensor_msgs/LaserScan   the lidar (scan_crop cuts it into /scan)
  out  /range/<name>     sensor_msgs/Range       each VL53L0X / HC-SR04 of sensors.yaml
  out  /sim/world        std_msgs/String   JSON: room, obstacles, pose, noise, scenes, bump, error (latched)
  out  /sim/sensors      std_msgs/String   JSON list of the sensors being simulated (latched)

    ros2 run r2_sim sim_world
"""

import json
import math
import os
import re
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import LaserScan, Range
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

from r2_shadow_bridge.protocol import units_to_twist
from r2_sensors.config import Reloader, config_path
from r2_sim.world import SensorSim, World, blocked_move, parse_foot, step_pose

SCENES = os.path.expanduser("~/.config/ros2d2/scenes")
NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
FOOT_LASTS = 0.3          # s, like the Mega's own timeout
CTL_FIFO = "/tmp/r2sim-mega-ctl"


class SimWorld(Node):
    def __init__(self):
        super().__init__("sim_world")
        p = self.declare_parameter
        p("drive_units_per_mps", 50.0)     # the bridge's foot calibration, to turn units back into m/s
        p("turn_units_per_radps", 30.0)
        p("scan_step_deg", 1.0)            # 1 deg keeps the Pi easy at 10 Hz
        p("seed", -1)                      # -1 = random
        p("mega_ctl", CTL_FIFO)            # the fake Mega's button FIFO
        seed = self.get_parameter("seed").value
        self.sim = SensorSim(None if seed < 0 else seed)
        self.world = World.default()
        default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
        self.reloader = Reloader(lambda: config_path(default))
        self.sensors = self.reloader.poll() or {}
        self.foot = None                   # (time, drive, turn)
        self.bump = False
        self.error = None

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_odom = self.create_publisher(Odometry, "/odom", 10)
        self.pub_tf = self.create_publisher(TFMessage, "/tf", 10)
        self.pub_scan = self.create_publisher(LaserScan, "/scan_raw", 10)
        self.pub_world = self.create_publisher(String, "/sim/world", latched)
        self.pub_list = self.create_publisher(String, "/sim/sensors", latched)
        self.pub_range = {}
        self.create_subscription(String, "/mega/tx", self._on_tx, 50)
        self.create_subscription(String, "/sim/world_cmd", self._on_cmd, 10)
        self._sensors_changed()
        self.create_timer(1.0, self._reload)
        self.create_timer(1.0, self._publish_world)
        self.create_timer(0.1, self._tick)
        self.last = time.monotonic()
        self._publish_world()

    def _sensors_changed(self):
        names = [n for n, s in self.sensors.items() if s["type"] != "rplidar_c1"]
        for n in names:
            if n not in self.pub_range:
                self.pub_range[n] = self.create_publisher(Range, f"/range/{n}", 10)
        self.pub_list.publish(String(data=json.dumps(sorted(self.sensors))))

    def _reload(self):
        s = self.reloader.poll()
        if s is not None:
            self.sensors = s
            self._sensors_changed()

    # ---------- inputs ----------
    def _on_tx(self, m):
        foot = parse_foot(m.data)
        if foot is not None:
            self.foot = (time.monotonic(), *foot)

    def _on_cmd(self, m):
        try:
            cmd = json.loads(m.data)
        except ValueError:
            cmd = {}
        op = cmd.get("op")
        if op in ("save", "load"):
            self.error = self._scene(op, cmd.get("name", ""))
        elif op == "press":
            self.error = self._press(cmd.get("what", ""))
        else:
            self.error = self.world.apply(cmd)
        if self.error:
            self.get_logger().warning(f"world_cmd {m.data}: {self.error}")
        self._publish_world()

    def _scene(self, op, name):
        if not NAME.match(name):
            return "scene name: letters, digits, - and _"
        path = os.path.join(SCENES, name + ".json")
        if op == "save":
            os.makedirs(SCENES, exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(self.world.to_json())
            os.replace(tmp, path)
            return None
        try:
            with open(path, encoding="utf-8") as f:
                noise = self.world.noise
                self.world = World.from_json(f.read())
                self.world.noise = noise
        except (OSError, ValueError) as e:
            return f"scene {name}: {e}"
        return None

    def _press(self, what):
        """The fake Mega's controller: button (PS + L2), stick, controller (lost)."""
        if what not in ("button", "stick", "controller"):
            return "press: button, stick or controller"
        try:
            fd = os.open(self.get_parameter("mega_ctl").value, os.O_WRONLY | os.O_NONBLOCK)
            os.write(fd, (what + "\n").encode())
            os.close(fd)
        except OSError as e:
            return f"press: the fake Mega is not running ({e.strerror})"
        return None

    # ---------- the 10 Hz loop ----------
    def _tick(self):
        now = time.monotonic()
        dt = min(0.5, now - self.last)
        self.last = now
        v = w = 0.0
        if self.foot and now - self.foot[0] < FOOT_LASTS:
            v, w = units_to_twist(self.foot[1], self.foot[2],
                                  self.get_parameter("drive_units_per_mps").value,
                                  self.get_parameter("turn_units_per_radps").value)
        nxt = step_pose(self.world.pose, v, w, dt)
        bump = blocked_move(self.world, nxt) and (v != 0)
        if bump:
            nxt = (self.world.pose[0], self.world.pose[1], nxt[2])   # can still turn on the spot
        if bump != self.bump:
            self.bump = bump
            self._publish_world()
        self.world.pose = list(nxt)
        stamp = self.get_clock().now().to_msg()
        self._publish_pose(stamp, v, w)
        self._publish_sensors(stamp)

    def _publish_pose(self, stamp, v, w):
        x, y, th = self.world.pose
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

    def _publish_sensors(self, stamp):
        pose = self.world.pose
        for name, s in self.sensors.items():
            if s["type"] == "rplidar_c1":
                a0, inc, ranges = self.sim.scan(self.world, pose, s, self.get_parameter("scan_step_deg").value)
                m = LaserScan()
                m.header.stamp, m.header.frame_id = stamp, f"{name}_link"
                m.angle_min, m.angle_increment = a0, inc
                m.angle_max = a0 + inc * (len(ranges) - 1)
                m.scan_time, m.time_increment = 0.1, 0.1 / len(ranges)
                m.range_min, m.range_max = s["range_min"], s["range_max"]
                m.ranges = ranges
                self.pub_scan.publish(m)
            elif name in self.pub_range:
                d = self.sim.range_of(self.world, pose, s)
                r = Range()
                r.header.stamp, r.header.frame_id = stamp, f"{name}_link"
                r.radiation_type = Range.ULTRASOUND if s["type"] == "hcsr04" else Range.INFRARED
                r.field_of_view = math.radians(s["fov_deg"])
                r.min_range, r.max_range = s["range_min"], s["range_max"]
                r.range = math.inf if d is None else float(d)
                self.pub_range[name].publish(r)

    def _publish_world(self):
        scenes = sorted(f[:-5] for f in os.listdir(SCENES) if f.endswith(".json")) if os.path.isdir(SCENES) else []
        d = json.loads(self.world.to_json())
        d.update({"scenes": scenes, "bump": self.bump, "error": self.error})
        self.pub_world.publish(String(data=json.dumps(d)))


def main():
    rclpy.init()
    node = SimWorld()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
