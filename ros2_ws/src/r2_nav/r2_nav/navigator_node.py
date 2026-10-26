"""The navigator node: drives the feet towards a goal with the logic in nav_core, only while
the autonomous mode is on (switched on with the controller, PS + L2).

  in   /nav/goal          geometry_msgs/PoseStamped  where to go (frame odom)
  in   /nav/cancel        std_msgs/Empty             forget the goal
  in   /odom              nav_msgs/Odometry          where R2 is (the simulator, later the odometry)
  in   /scan              sensor_msgs/LaserScan      the lidar, already cut to what R2 does not hide
  in   /range/<name>      sensor_msgs/Range          each distance sensor of sensors.yaml
  in   /r2/auto_mode      std_msgs/Bool              from the Mega bridge (latched)
  out  /foot/cmd_vel      geometry_msgs/Twist        10 Hz, with acceleration ramps
  out  /mega/command      std_msgs/String            the sound of each event (S1:$..)
  out  /nav/state         std_msgs/String            JSON for the web console (see nav_core.state_json)

Parameters: every key of nav.yaml (sounds as sounds.<event>), changeable live; `config`.

    ros2 run r2_nav navigator
"""

import math
import os

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, Range
from std_msgs.msg import Bool, Empty, String

from r2_nav.nav_core import (BLOCKED_MODES, DEFAULTS, EVENTS, RANGES, SOUND, Navigator, NavConfigError, RangeFilter, clamp_param,
                             config_path, is_lidar, load_nav, ramp, state_json)
from r2_sensors.config import Reloader
from r2_sensors.config import config_path as sensors_path

STALE = 0.5          # s: a sensor older than this is not reporting
TURN_ACCEL = 2.5     # rad/s²


class NavigatorNode(Node):
    def __init__(self):
        super().__init__("navigator")
        default = os.path.join(get_package_share_directory("r2_nav"), "config", "nav.yaml")
        path = config_path(self.declare_parameter("config", default).value)
        try:
            cfg = load_nav(path)
        except (OSError, NavConfigError) as e:
            self.get_logger().error(f"nav.yaml: {e} (using the defaults)")
            cfg = load_nav(default)
        for k, v in cfg.items():
            if k == "sounds":
                for ev in EVENTS:
                    self.declare_parameter(f"sounds.{ev}", v[ev])
            else:
                self.declare_parameter(k, v)
        self.cfg = cfg
        self.add_on_set_parameters_callback(self._on_params)

        sensors_default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
        self.sensors_reloader = Reloader(lambda: sensors_path(sensors_default))
        self.sensors = self.sensors_reloader.poll() or {}
        self.nav = Navigator(cfg, self.sensors)

        self.pose = (0.0, 0.0, 0.0)
        self.auto_on = False
        self.scan = None            # (time, points in base_link)
        self.ranges = {}            # name -> (time, metres | None)
        self.filters = {}
        self.range_subs = {}
        self.out = (0.0, 0.0)
        self.last = None

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_cmd = self.create_publisher(Twist, "/foot/cmd_vel", 10)
        self.pub_sound = self.create_publisher(String, "/mega/command", 10)
        self.pub_state = self.create_publisher(String, "/nav/state", 10)
        self.create_subscription(PoseStamped, "/nav/goal", self._on_goal, 10)
        self.create_subscription(Empty, "/nav/cancel", lambda _m: self.nav.cancel(), 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)
        self.create_subscription(Bool, "/r2/auto_mode", self._on_auto, latched)
        self._subscribe_ranges()
        self.create_timer(1.0, self._reload_sensors)
        self.create_timer(0.1, self._tick)
        self.get_logger().info(f"navigator ready ({path})")

    # ---------- inputs ----------
    def _subscribe_ranges(self):
        for name, s in self.sensors.items():
            if is_lidar(s) or name in self.range_subs:
                continue
            self.range_subs[name] = self.create_subscription(
                Range, f"/range/{name}", lambda m, n=name: self._on_range(n, m), qos_profile_sensor_data)

    def _reload_sensors(self):
        sensors = self.sensors_reloader.poll()
        if sensors is not None:
            self.sensors = sensors
            self.nav.reconfigure(sensors=sensors)
            self._subscribe_ranges()

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_goal(self, m):
        self.nav.set_goal(m.pose.position.x, m.pose.position.y)
        self.get_logger().info(f"goal {m.pose.position.x:.2f}, {m.pose.position.y:.2f}")

    def _on_odom(self, m):
        q = m.pose.pose.orientation
        th = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        self.pose = (m.pose.pose.position.x, m.pose.pose.position.y, th)

    def _on_auto(self, m):
        self.auto_on = m.data

    def _on_scan(self, m):
        lidar = next((s for s in self.sensors.values() if is_lidar(s)), None)
        lx, ly, ly_aw = (lidar["x"], lidar["y"], math.radians(lidar["yaw_deg"])) if lidar else (0.0, 0.0, 0.0)
        pts = []
        for i, r in enumerate(m.ranges):
            if not math.isfinite(r) or r < m.range_min or r > m.range_max:
                continue
            a = m.angle_min + i * m.angle_increment + ly_aw
            pts.append((lx + r * math.cos(a), ly + r * math.sin(a)))
        self.scan = (self._now(), pts)

    def _on_range(self, name, m):
        r = m.range
        seen = math.isfinite(r) and m.min_range <= r <= m.max_range
        self.ranges[name] = (self._now(), r if seen else None)

    def _on_params(self, params):
        cfg = dict(self.cfg)
        cfg["sounds"] = dict(self.cfg["sounds"])
        for p in params:
            if p.name == "config":
                continue
            if p.name.startswith("sounds."):
                ev = p.name.split(".", 1)[1]
                if ev not in EVENTS or (p.value and not SOUND.match(str(p.value))):
                    return SetParametersResult(successful=False, reason=f"{p.name}: must be empty or like S1:$11")
                cfg["sounds"][ev] = p.value or ""
            elif p.name in DEFAULTS:
                # out of range is refused (not silently clamped: the parameter would lie)
                if p.name in RANGES and clamp_param(p.name, p.value) != p.value:
                    lo, hi = RANGES[p.name]
                    return SetParametersResult(successful=False, reason=f"{p.name}: must be from {lo} to {hi}")
                if p.name == "on_blocked" and p.value not in BLOCKED_MODES:
                    return SetParametersResult(successful=False, reason=f"on_blocked: one of {', '.join(BLOCKED_MODES)}")
                cfg[p.name] = p.value
        self.cfg = cfg
        self.nav.reconfigure(cfg=cfg)
        return SetParametersResult(successful=True)

    # ---------- the 10 Hz loop ----------
    def _tick(self):
        now = self._now()
        dt = 0.1 if self.last is None else max(0.01, min(0.5, now - self.last))
        self.last = now
        scan_xy = self.scan[1] if self.scan and now - self.scan[0] < STALE else None
        ranges, raw, filtered = {}, {}, {}
        for name, (t, r) in self.ranges.items():
            if now - t >= STALE:
                continue
            raw[name] = r
            if self.cfg["filter"]:
                r = self.filters.setdefault(name, RangeFilter()).update(r)
            ranges[name] = r
            filtered[name] = r
        d = self.nav.step(now, self.pose, scan_xy, ranges, self.auto_on)

        v, w = self.out
        if not self.auto_on:
            v, w = 0.0, 0.0
        else:
            v = ramp(v, d.v, self.cfg["accel"] * dt)
            w = ramp(w, d.w, TURN_ACCEL * dt)
            if d.state == "stop" and d.v == 0:
                v = min(v, 0.0)                      # a stop is a stop: no ramp down
            if not self.cfg["allow_reverse"]:
                v = max(0.0, v)
        self.out = (v, w)
        t = Twist()
        t.linear.x, t.angular.z = v, w
        self.pub_cmd.publish(t)

        for ev in d.events:
            cmd = self.cfg["sounds"].get(ev, "")
            if cmd:
                self.pub_sound.publish(String(data=cmd))
        d.v, d.w = v, w
        heading = None if d.heading is None else self.pose[2] + d.heading
        self.pub_state.publish(String(data=state_json(d, self.nav.goal, heading, filtered, raw)))


def main():
    rclpy.init()
    node = NavigatorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
