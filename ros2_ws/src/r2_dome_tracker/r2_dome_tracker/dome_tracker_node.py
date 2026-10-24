"""R2 dome tracker node: turns the dome to look at the closest face.

Topics:
  in   /cameras/<camera>/faces         vision_msgs/Detection2DArray  (biggest face first)
  in   /cameras/<camera>/camera_info   sensor_msgs/CameraInfo        (picture width)
  out  /dome/speed_cmd                 std_msgs/Int16   ShadowMD DM: units, ~15 per second
                                                        while enabled; the Mega bridge turns
                                                        it into DM:<speed>
  in   /r2/auto_mode                   std_msgs/Bool    autonomous mode (latched); off = the dome is left alone
  out  ~/status                        std_msgs/String  disabled | auto off | no face | tracking

All gains can be changed while running (ros2 param set, or the web console).
"""

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import Bool, Int16, String
from vision_msgs.msg import Detection2DArray

from r2_dome_tracker.control import DomeTracker, Gains, face_error

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

        self.tracker = DomeTracker(self._gains())
        self.width = None
        self._was_enabled = False

        cam = self.get_parameter("camera").value
        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(Detection2DArray, f"/cameras/{cam}/faces", self._on_faces, 10)
        self.create_subscription(CameraInfo, f"/cameras/{cam}/camera_info", self._on_info, sensor_qos)
        # The dome follows faces only in autonomous mode (switched on from the controller).
        # Latched by the Mega bridge; until it says otherwise the mode counts as off.
        self.auto_on = False
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Bool, "/r2/auto_mode", self._on_auto_mode, latched)
        self.pub_speed = self.create_publisher(Int16, "/dome/speed_cmd", 10)
        self.pub_status = self.create_publisher(String, "~/status", 10)

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
        if new.get("rate_hz", 1) <= 0:
            return SetParametersResult(successful=False, reason="rate_hz must be > 0")
        if "camera" in new:
            return SetParametersResult(successful=False, reason="camera is fixed at start; relaunch to change it")
        return SetParametersResult(successful=True)

    def _after_params(self, params):
        names = {prm.name for prm in params}
        if names & GAIN_PARAMS:
            self.tracker.gains = self._gains()
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
        if msg.detections:
            cx = msg.detections[0].bbox.center.position.x
            self.tracker.face(face_error(cx, self.width), t)
        else:
            self.tracker.no_face()

    def _on_auto_mode(self, msg):
        self.auto_on = msg.data

    def _tick(self):
        if not self.param("enabled") or not self.auto_on:
            if self._was_enabled:
                self.pub_speed.publish(Int16(data=0))   # one stop, then quiet: the controller is free
                self.tracker.reset()
            self._was_enabled = False
            self.pub_status.publish(String(data="disabled" if not self.param("enabled") else "auto off"))
            return
        self._was_enabled = True
        now = self.get_clock().now().nanoseconds / 1e9
        speed = self.tracker.speed(now)
        self.pub_speed.publish(Int16(data=speed))
        self.pub_status.publish(String(data="tracking" if self.tracker.has_target(now) else "no face"))


def main():
    rclpy.init()
    node = DomeTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub_speed.publish(Int16(data=0))
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
