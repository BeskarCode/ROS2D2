# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The wander node: the head of Patrol and Free roam (logic in wander_core). It chooses the course
and the stops; the navigator drives it with all its safety. Only while Patrol or Free roam is on
with the autonomous mode on; otherwise silent (one stop for the dome on the way out).

  in   /r2/mode, /r2/auto_mode            which mode is on (latched, from the Mega bridge)
  in   /odom                               where R2 is
  in   /nav/state                          the navigator: blocked ("searching", "gave up") or not
  in   /cameras/<cam>/faces, camera_info   the faces, as the dome tracker reads them
  in   /dome/angle_estimate                the dome's angle (the dome tracker counts every speed sent)
  out  /wander/heading   std_msgs/Float32  the course, rad in odom
  out  /wander/hold      std_msgs/Bool     feet still (looking round, saying hello)
  out  /dome/speed_cmd   std_msgs/Int16    the dome (DM: units)
  out  /mega/command     std_msgs/String   the hello and the idle sounds
  out  /wander/state     std_msgs/String   JSON for the console: state, home_dist, radius, start, mode

Parameters: wander.<key> of nav.yaml (changeable live), config (nav.yaml), dome_config (the dome
tracker's gains and face lock), cameras_config (cameras.yaml).

    ros2 run r2_nav wander
"""

import json
import math
import os
import random

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import Bool, Float32, Int16, String
from vision_msgs.msg import Detection2DArray

from r2_dome_tracker.control import Gains, bearing_deg, face_error
from r2_dome_tracker.dome_tracker_node import cameras_from_config
from r2_nav.nav_core import NavConfigError, config_path, declare_wander, load_nav, wander_param_error
from r2_nav.spin import spin
from r2_nav.wander_core import Wander, leave_outputs, wander_active

ODOM_STALE = 0.5     # s
RATE_HZ = 15.0       # the Mega stops the dome 300 ms without an order: well inside that
STATE_EVERY = 0.2    # s between two /wander/state


def dome_settings(path):
    """(Gains, lock_gate_deg, lock_calm_s) from the dome tracker's yaml; defaults for what is missing."""
    g = Gains()
    try:
        with open(path, encoding="utf-8") as f:
            p = (yaml.safe_load(f) or {}).get("dome_tracker", {}).get("ros__parameters", {})
    except (OSError, yaml.YAMLError, AttributeError):
        p = {}
    gains = Gains(min_speed=int(p.get("min_speed", g.min_speed)), max_speed=int(p.get("max_speed", g.max_speed)),
                  kd=float(p.get("kd", g.kd)), deadzone=float(p.get("deadzone", g.deadzone)),
                  invert=bool(p.get("invert", g.invert)), lost_after=float(p.get("lost_after", g.lost_after)))
    return gains, float(p.get("lock_gate_deg", 15.0)), float(p.get("lock_calm_s", 2.0))


class WanderNode(Node):
    def __init__(self):
        super().__init__("wander")
        share = get_package_share_directory
        default = os.path.join(share("r2_nav"), "config", "nav.yaml")
        path = config_path(self.declare_parameter("config", default).value)
        try:
            self.cfg = load_nav(path)["wander"]
        except (OSError, NavConfigError) as e:
            self.get_logger().error(f"nav.yaml: {e} (using the defaults)")
            self.cfg = load_nav(default)["wander"]
        declare_wander(self, self.cfg)
        self.add_on_set_parameters_callback(self._on_params)
        dome_cfg = self.declare_parameter(
            "dome_config", os.path.join(share("r2_dome_tracker"), "config", "dome_tracker.yaml")).value
        self.gains, self.lock_gate, self.lock_calm = dome_settings(dome_cfg)
        cams_cfg = self.declare_parameter(
            "cameras_config", os.path.join(share("r2_camera"), "config", "cameras.yaml")).value
        self.cams = cameras_from_config(cams_cfg)      # {name: (yaw_deg, hfov_deg)}

        self.mode, self.auto_on = "", False
        self.pose, self.odom_t = None, None
        self.nav_state = None
        self.dome_deg = 0.0
        self.width, self.latest = {}, {}
        self.head = None              # the Wander of the mode that is on
        self.active = False
        self.last_state = 0.0

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
        self.pub_heading = self.create_publisher(Float32, "/wander/heading", 10)
        self.pub_hold = self.create_publisher(Bool, "/wander/hold", 10)
        self.pub_dome = self.create_publisher(Int16, "/dome/speed_cmd", 10)
        self.pub_sound = self.create_publisher(String, "/mega/command", 10)
        self.pub_state = self.create_publisher(String, "/wander/state", 10)
        self.create_subscription(String, "/r2/mode", lambda m: setattr(self, "mode", m.data), latched)
        self.create_subscription(Bool, "/r2/auto_mode", lambda m: setattr(self, "auto_on", m.data), latched)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(String, "/nav/state", self._on_nav_state, 10)
        self.create_subscription(Float32, "/dome/angle_estimate", lambda m: setattr(self, "dome_deg", m.data), 10)
        for cam in self.cams:
            self.create_subscription(Detection2DArray, f"/cameras/{cam}/faces", lambda m, c=cam: self._on_faces(c, m), 10)
            self.create_subscription(CameraInfo, f"/cameras/{cam}/camera_info",
                                     lambda m, c=cam: self.width.__setitem__(c, m.width), sensor_qos)
        self.create_timer(1.0 / RATE_HZ, self._tick)
        self.get_logger().info(f"wander ready (cameras: {', '.join(self.cams) or 'none'})")

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_params(self, params):
        for p in params:
            if p.name.startswith("wander."):
                key = p.name.split(".", 1)[1]
                value = list(p.value) if isinstance(p.value, (list, tuple)) or hasattr(p.value, "tolist") else p.value
                err = wander_param_error(key, value)
                if err:
                    return SetParametersResult(successful=False, reason=err)
                self.cfg[key] = value              # the running head reads this same dict
        return SetParametersResult(successful=True)

    def _on_odom(self, m):
        q = m.pose.pose.orientation
        th = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        self.pose = (m.pose.pose.position.x, m.pose.pose.position.y, th)
        self.odom_t = self._now()

    def _on_nav_state(self, m):
        try:
            self.nav_state = json.loads(m.data).get("state")
        except (ValueError, AttributeError):
            self.nav_state = None

    def _on_faces(self, cam, msg):
        width = self.width.get(cam)
        if not width:
            return
        t = Time.from_msg(msg.header.stamp).nanoseconds * 1e-9
        yaw, hfov = self.cams[cam]
        self.latest[cam] = [(t, bearing_deg(face_error(d.bbox.center.position.x, width), yaw, hfov), d.bbox.size_x / width)
                            for d in msg.detections]

    def _tick(self):
        now = self._now()
        active = wander_active(self.mode, self.auto_on)
        for what, value in leave_outputs(self.active, active):
            if what == "dome":
                self.pub_dome.publish(Int16(data=value))
        if active and not self.active:
            self.head = Wander(self.cfg, self.gains, random.Random(), self.mode == "patrol", self.lock_gate, self.lock_calm)
            self.head.start(now, self._pose(now))
            self.get_logger().info(f"{self.mode}: strolling")
        self.active = active
        if not active:
            self.head = None
            return
        faces = [f for got in self.latest.values() for f in got if now - f[0] <= self.gains.lost_after]
        out = self.head.step(now, self._pose(now), self.nav_state, faces, self.dome_deg)
        if out.heading is not None:
            self.pub_heading.publish(Float32(data=float(out.heading)))
        self.pub_hold.publish(Bool(data=out.hold))
        self.pub_dome.publish(Int16(data=int(out.dome)))
        for s in out.sounds:
            self.pub_sound.publish(String(data=s))
        if now - self.last_state >= STATE_EVERY:
            self.last_state = now
            r = lambda v: None if v is None else round(v, 2)   # noqa: E731
            self.pub_state.publish(String(data=json.dumps({
                "mode": self.mode, "state": out.state, "home_dist": r(out.home_dist),
                "radius": self.cfg["radius"] if self.mode == "patrol" else None,
                "start": None if self.head.origin is None else [r(v) for v in self.head.origin]})))

    def _pose(self, now):
        return self.pose if self.odom_t is not None and now - self.odom_t < ODOM_STALE else None


def main():
    rclpy.init()
    node = WanderNode()
    try:
        spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok() and node.active:
            node.pub_dome.publish(Int16(data=0))
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
