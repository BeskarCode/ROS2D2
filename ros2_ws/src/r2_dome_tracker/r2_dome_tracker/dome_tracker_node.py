"""R2 dome tracker node: turns the dome to look at the closest face.

Topics:
  in   /cameras/<camera>/faces         vision_msgs/Detection2DArray  (biggest face first)
  in   /cameras/<camera>/camera_info   sensor_msgs/CameraInfo        (picture width)
  out  /dome/speed_cmd                 std_msgs/Int16   ShadowMD DM: units, ~15 per second
                                                        while enabled; the Mega bridge turns
                                                        it into DM:<speed>
  in   /r2/track_mode                  std_msgs/Bool    face tracking, PS + L2 on the dome Nav (latched);
                                                        off = the dome is left alone. Independent of
                                                        the autonomous mode of the feet
  out  ~/status                        std_msgs/String  disabled | track off | no face | tracking
  out  /dome/angle_estimate            std_msgs/Float32 degrees, + = right; worked out from the speeds
                                                        sent, as the dome has no position sensor
  in   /dome/angle_reset               std_msgs/Empty   "the dome is facing front now": angle = 0

simulate:=true closes the loop without a Mega: the faces are shifted as if the camera
had turned with the estimated dome angle, so the (virtual) dome stops when it faces you.

All gains can be changed while running (ros2 param set, or the web console).
"""

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import Bool, Empty, Float32, Int16, String
from vision_msgs.msg import Detection2DArray

from r2_dome_tracker.control import DomeEstimate, DomeTracker, Gains, face_error, simulated_error

GAIN_PARAMS = {"min_speed", "max_speed", "kd", "deadzone", "invert", "lost_after"}


class DomeTrackerNode(Node):
    def __init__(self):
        super().__init__("dome_tracker")
        g = Gains()
        p = self.declare_parameter
        p("camera", "front", ParameterDescriptor(description="Camera whose faces the dome follows"))
        p("enabled", True)
        p("rate_hz", 15.0, ParameterDescriptor(
            description="How often the speed is sent; the Mega stops the dome after 300 ms without one"))
        p("min_speed", g.min_speed, ParameterDescriptor(description="Speed just outside the dead zone"))
        p("max_speed", g.max_speed, ParameterDescriptor(description="Speed with the face at the edge"))
        p("kd", g.kd, ParameterDescriptor(
            description="How much the face's own speed counts, seconds: higher = catches up and brakes sooner"))
        p("deadzone", g.deadzone, ParameterDescriptor(description="Centre band with no movement, 0-1"))
        p("invert", g.invert, ParameterDescriptor(description="Turn the other way"))
        p("lost_after", g.lost_after, ParameterDescriptor(description="No face for this long: stop, seconds"))
        p("deg_per_s_at_80", 90.0, ParameterDescriptor(
            description="How fast the dome turns at speed 80, for the angle estimate: 360 / seconds per turn"))
        p("simulate", False, ParameterDescriptor(
            description="No Mega: shift the faces by the estimated dome angle so the loop closes"))
        p("camera_hfov_deg", 60.0, ParameterDescriptor(description="Horizontal field of view, for simulate"))

        self.tracker = DomeTracker(self._gains())
        self.dome = DomeEstimate(self.param("deg_per_s_at_80"))
        self._last_tick = None
        self.width = None
        self._was_enabled = False

        cam = self.get_parameter("camera").value
        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(Detection2DArray, f"/cameras/{cam}/faces", self._on_faces, 10)
        self.create_subscription(CameraInfo, f"/cameras/{cam}/camera_info", self._on_info, sensor_qos)
        # The dome follows faces only with face tracking on (switched on from the dome Nav).
        # Latched by the Mega bridge; until it says otherwise it counts as off.
        self.track_on = False
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Bool, "/r2/track_mode", self._on_track_mode, latched)
        self.pub_speed = self.create_publisher(Int16, "/dome/speed_cmd", 10)
        self.pub_status = self.create_publisher(String, "~/status", 10)
        self.pub_angle = self.create_publisher(Float32, "/dome/angle_estimate", 10)
        self.create_subscription(Empty, "/dome/angle_reset", lambda _: self.dome.reset(), 10)

        self.add_on_set_parameters_callback(self._check_params)
        self.add_post_set_parameters_callback(self._after_params)
        self._timer = self.create_timer(1.0 / self.get_parameter("rate_hz").value, self._tick)
        self.get_logger().info(f"following faces from camera '{cam}'")

    def param(self, name):
        return self.get_parameter(name).value

    def _gains(self):
        return Gains(min_speed=self.param("min_speed"), max_speed=self.param("max_speed"),
                     kd=self.param("kd"), deadzone=self.param("deadzone"),
                     invert=self.param("invert"), lost_after=self.param("lost_after"))

    def _check_params(self, params):
        new = {prm.name: prm.value for prm in params}
        lo = new.get("min_speed", self.param("min_speed"))
        hi = new.get("max_speed", self.param("max_speed"))
        if not 0 <= lo <= hi <= 127:
            return SetParametersResult(successful=False, reason="need 0 <= min_speed <= max_speed <= 127")
        if not 0 <= new.get("deadzone", 0) < 1:
            return SetParametersResult(successful=False, reason="deadzone must be 0-1")
        if new.get("deg_per_s_at_80", 1) <= 0 or not 0 < new.get("camera_hfov_deg", 60) < 180:
            return SetParametersResult(successful=False, reason="need deg_per_s_at_80 > 0, 0 < camera_hfov_deg < 180")
        if new.get("rate_hz", 1) <= 0:
            return SetParametersResult(successful=False, reason="rate_hz must be > 0")
        if "camera" in new:
            return SetParametersResult(successful=False, reason="camera is fixed at start; relaunch to change it")
        return SetParametersResult(successful=True)

    def _after_params(self, params):
        names = {prm.name for prm in params}
        if names & GAIN_PARAMS:
            self.tracker.gains = self._gains()
        if "deg_per_s_at_80" in names:
            self.dome.deg_per_s_at_80 = self.param("deg_per_s_at_80")
        if "rate_hz" in names:
            self._timer.cancel()
            self._timer = self.create_timer(1.0 / self.param("rate_hz"), self._tick)

    def _on_info(self, msg):
        self.width = msg.width

    def _on_faces(self, msg):
        if self.width is None:
            self.get_logger().warn("no camera_info yet, waiting for the picture width",
                                   throttle_duration_sec=10.0)
            return
        t = Time.from_msg(msg.header.stamp).nanoseconds / 1e9   # when the picture was taken
        err = None
        if msg.detections:
            err = face_error(msg.detections[0].bbox.center.position.x, self.width)
            if self.param("simulate"):
                err = simulated_error(err, self.dome.angle, self.param("camera_hfov_deg"))
        if err is None:
            self.tracker.no_face()
        else:
            self.tracker.face(err, t)

    def _on_track_mode(self, msg):
        self.track_on = msg.data

    def _tick(self):
        now = self.get_clock().now().nanoseconds / 1e9
        dt = 0.0 if self._last_tick is None else now - self._last_tick
        self._last_tick = now
        speed = self._step(now)
        self.dome.update(speed, self.param("invert"), dt)
        self.pub_angle.publish(Float32(data=float(self.dome.angle)))

    def _step(self, now):
        """Publish this tick's speed and status; returns the speed the dome turns at."""
        if not self.param("enabled") or not self.track_on:
            if self._was_enabled:
                self.pub_speed.publish(Int16(data=0))   # one stop, then quiet: the controller is free
                self.tracker.reset()
            self._was_enabled = False
            self.pub_status.publish(String(data="disabled" if not self.param("enabled") else "track off"))
            return 0
        self._was_enabled = True
        speed = self.tracker.speed(now)
        self.pub_speed.publish(Int16(data=speed))
        self.pub_status.publish(String(data="tracking" if self.tracker.has_target(now) else "no face"))
        return speed


def main():
    rclpy.init()
    node = DomeTrackerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():          # after an external shutdown the context is gone
            node.pub_speed.publish(Int16(data=0))
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
