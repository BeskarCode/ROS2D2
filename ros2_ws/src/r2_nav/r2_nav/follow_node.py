# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The follow node: drives the feet and the dome after the colour marker, with the logic in
follow_core, only while the mode is follow ("Follow a colour", started with the controller).

  in   /r2/mode           std_msgs/String            which mode is on (latched)
  in   /marker            std_msgs/String            JSON {seen, bearing, area, cx, cy, t} (color_marker)
  in   /scan              sensor_msgs/LaserScan      the lidar, already cut to what R2 does not hide
  in   /range/<name>      sensor_msgs/Range          each distance sensor of sensors.yaml
  in   /r2/modes/reload   std_msgs/Empty             re-read modes.yaml and nav.yaml
  out  /foot/cmd_vel      geometry_msgs/Twist        10 Hz while mode == follow; one zero on leaving
  out  /dome/speed_cmd    std_msgs/Int16             DM: units, same
  out  /mega/command      std_msgs/String            sound_lost / sounds.blocked (S1:$..)
  out  /follow/state      std_msgs/String            JSON {state, v, w, distance, bearing}, 5 Hz

The ramps are applied by follow_core: what it decides goes out as is.

    ros2 run r2_nav follow
"""

import json
import math
import os

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, Range
from std_msgs.msg import Bool, Empty, Int16, String

from r2_nav.lidar_gate import LidarGate, motor_policy
from r2_nav.follow_core import Follower
from r2_nav.modes import drives_in, load_modes, modes_path
from r2_nav.nav_core import NavConfigError, RangeFilter, config_path, is_lidar, load_nav
from r2_sensors.config import Reloader, in_use
from r2_sensors.config import config_path as sensors_path

STALE = 0.5          # s: a sensor older than this is not reporting


class FollowNode(Node):
    def __init__(self):
        super().__init__("follow")
        share = get_package_share_directory("r2_nav")
        self.nav_default = os.path.join(share, "config", "nav.yaml")
        self.modes_default = os.path.join(share, "config", "modes.yaml")
        self.declare_parameter("config", self.nav_default)
        self.nav_path = config_path(self.get_parameter("config").value)
        self.nav_cfg, self.follow_cfg, self.mtimes = None, None, {}
        self._load()

        sensors_default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
        self.sensors_reloader = Reloader(lambda: sensors_path(sensors_default))
        self.sensors = self.sensors_reloader.poll() or {}
        self.follower = Follower(self.follow_cfg, self.nav_cfg, in_use(self.sensors))
        self.gate = LidarGate(motor_policy(in_use(self.sensors)))   # with_modes: wait for the lidar to spin up

        self.mode = None
        self.active = False
        self.marker = None
        self.scan = None            # (time, points in base_link)
        self.ranges = {}            # name -> (time, metres | None)
        self.filters = {}
        self.range_subs = {}
        self.last_state = 0.0

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_cmd = self.create_publisher(Twist, "/foot/cmd_vel", 10)
        self.pub_dome = self.create_publisher(Int16, "/dome/speed_cmd", 10)
        self.pub_sound = self.create_publisher(String, "/mega/command", 10)
        self.pub_state = self.create_publisher(String, "/follow/state", 10)
        self.create_subscription(String, "/r2/mode", self._on_mode, latched)
        # the Mega moves the feet only with auto on: that is when the lidar must already be spinning
        self.auto_on = False
        self.create_subscription(Bool, "/r2/auto_mode", lambda m: setattr(self, "auto_on", m.data), latched)
        self.create_subscription(String, "/marker", self._on_marker, 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)
        self.create_subscription(Empty, "/r2/modes/reload", lambda _m: self._load(), 10)
        self._subscribe_ranges()
        self.create_timer(1.0, self._housekeeping)
        self.create_timer(0.1, self._tick)
        self.get_logger().info(f"follow ready ({self.nav_path}, {modes_path(self.modes_default)})")

    # ---------- configuration ----------
    def _load(self):
        """(Re)read nav.yaml and modes.yaml; a broken file keeps what was working."""
        mpath = modes_path(self.modes_default)
        try:
            nav = load_nav(self.nav_path)
        except (OSError, NavConfigError) as e:
            self.get_logger().error(f"nav.yaml: {e}")
            nav = self.nav_cfg or load_nav(self.nav_default)
        try:
            follow = load_modes(mpath)["follow"]
        except (OSError, ValueError) as e:
            self.get_logger().error(f"modes.yaml: {e}")
            follow = self.follow_cfg or load_modes(self.modes_default)["follow"]
        self.nav_cfg, self.follow_cfg = nav, follow
        self.mtimes = {p: self._mtime(p) for p in (self.nav_path, mpath)}
        if hasattr(self, "follower"):
            self.follower.reconfigure(follow_cfg=follow, nav_cfg=nav)

    @staticmethod
    def _mtime(path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return None

    def _housekeeping(self):
        if modes_path(self.modes_default) not in self.mtimes or any(
                self._mtime(p) != t for p, t in self.mtimes.items()):
            self._load()
        sensors = self.sensors_reloader.poll()
        if sensors is not None:
            self.sensors = sensors
            self.follower.reconfigure(sensors=in_use(sensors))
            self.gate.policy = motor_policy(in_use(sensors))
            self._subscribe_ranges()

    # ---------- inputs ----------
    def _subscribe_ranges(self):
        for name, s in self.sensors.items():
            if is_lidar(s) or name in self.range_subs:
                continue
            self.range_subs[name] = self.create_subscription(
                Range, f"/range/{name}", lambda m, n=name: self._on_range(n, m), qos_profile_sensor_data)

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_mode(self, m):
        self.mode = m.data

    def _on_marker(self, m):
        try:
            d = json.loads(m.data)
        except ValueError:
            return
        if isinstance(d, dict):
            self.marker = d

    def _on_scan(self, m):
        lidar = next((s for s in self.sensors.values() if is_lidar(s)), None)
        if lidar is not None and not lidar.get("enabled", True):
            self.scan = None              # the lidar is ignored: as if there were none
            return
        lx, ly, yaw = (lidar["x"], lidar["y"], math.radians(lidar["yaw_deg"])) if lidar else (0.0, 0.0, 0.0)
        pts = []
        for i, r in enumerate(m.ranges):
            if not math.isfinite(r) or r < m.range_min or r > m.range_max:
                continue
            a = m.angle_min + i * m.angle_increment + yaw
            pts.append((lx + r * math.cos(a), ly + r * math.sin(a)))
        self.scan = (self._now(), pts)
        self.gate.on_scan(self.scan[0])

    def _on_range(self, name, m):
        r = m.range
        seen = math.isfinite(r) and m.min_range <= r <= m.max_range
        self.ranges[name] = (self._now(), r if seen else None)

    # ---------- the 10 Hz loop ----------
    def _stop_outputs(self):
        self.pub_cmd.publish(Twist())
        self.pub_dome.publish(Int16(data=0))

    def _tick(self):
        if not drives_in(self.mode, "follow"):
            self.gate.update(self._now(), False)
            if self.active:                       # leaving follow: one zero of each, then silence
                self.active = False
                self._stop_outputs()
            return
        if not self.active:                       # entering: start from rest, with nothing stale
            self.active = True
            self.marker = None
            self.follower = Follower(self.follow_cfg, self.nav_cfg, in_use(self.sensors))
            self.follower.start(self._now())

        # armed when follow is on AND auto is on (follow can be chosen long before PS+L2)
        self.gate.update(self._now(), self.auto_on)
        if not self.gate.ready(self._now()):         # the lidar is spinning up: hold still (<= 5 s)
            return

        now = self._now()
        scan_xy = self.scan[1] if self.scan and now - self.scan[0] < STALE else None
        ranges = {}
        for name, (t, r) in self.ranges.items():
            if now - t >= STALE:
                continue
            if self.nav_cfg["filter"]:
                r = self.filters.setdefault(name, RangeFilter()).update(r)
            ranges[name] = r
        d = self.follower.step(now, self.marker, scan_xy, ranges)

        t = Twist()
        t.linear.x, t.angular.z = max(0.0, d.v), d.w         # never backwards
        self.pub_cmd.publish(t)
        self.pub_dome.publish(Int16(data=int(d.dome)))
        for ev in d.events:
            cmd = {"lost": self.follow_cfg.get("sound_lost", ""),
                   "blocked": self.nav_cfg["sounds"].get("blocked", "")}.get(ev, "")
            if cmd:
                self.pub_sound.publish(String(data=cmd))
        if now - self.last_state >= 0.2:
            self.last_state = now
            m = self.marker if self.marker and self.marker.get("seen") else None
            bearing = None if m is None else m.get("bearing")
            dist = None if m is None else self.follower._distance(bearing, m.get("area"), scan_xy)
            self.pub_state.publish(String(data=json.dumps({
                "state": d.state, "v": round(d.v, 3), "w": round(d.w, 3),
                "distance": None if dist is None else round(dist, 2),
                "bearing": None if bearing is None else round(bearing, 3)})))


def main():
    rclpy.init()
    node = FollowNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok() and node.active:
            node._stop_outputs()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
