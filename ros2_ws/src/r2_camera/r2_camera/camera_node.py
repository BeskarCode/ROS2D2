"""R2 camera node: one instance per camera.

Reads a USB webcam (V4L2) or a network stream (e.g. an ESP32 camera's MJPEG URL)
with OpenCV and publishes it as ROS images. Every picture carries the time it was
grabbed, so the nodes downstream can compensate for the camera's lag (lag is
what made the dome overshoot in the proof of concept).

Topics (relative to the node, e.g. /cameras/front/...):
  image_raw              sensor_msgs/Image (bgr8)        if publish_raw
  image_raw/compressed   sensor_msgs/CompressedImage     if publish_compressed
  camera_info            sensor_msgs/CameraInfo          picture size (uncalibrated)

Parameters can be changed while running (ros2 param set, or the web console);
changing the source or the picture size reopens the camera. `available_modes` lists the
sizes a USB camera offers in its pixel format ("640x480@30"), for the web console's menu.
"""

import threading
import time

import cv2
import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CameraInfo, CompressedImage, Image

from r2_camera.source import is_file, is_network, list_modes, open_capture, parse_source

# Changing one of these needs the camera reopened
REOPEN_PARAMS = {"source", "width", "height", "fps", "fourcc"}
ROTATIONS = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
             270: cv2.ROTATE_90_COUNTERCLOCKWISE}
FLIPS = {"none": None, "h": 1, "v": 0, "both": -1}


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera")
        p = self.declare_parameter
        p("source", "0", ParameterDescriptor(
            description="0, /dev/video0, /dev/v4l/by-id/..., an http(s)/rtsp URL, "
                        "or a video file (played in a loop at fps, for testing without a camera)"))
        p("width", 640)
        p("height", 480)
        p("fps", 30)
        p("fourcc", "MJPG", ParameterDescriptor(
            description="USB pixel format; MJPG gives full fps on most webcams. Empty = driver default"))
        p("frame_id", "camera")
        p("rotate", 0, ParameterDescriptor(description="0, 90, 180 or 270 degrees clockwise"))
        p("flip", "none", ParameterDescriptor(description="none, h, v or both"))
        p("publish_raw", True)
        p("publish_compressed", True, ParameterDescriptor(
            description="JPEG copy for the web console and for remote viewers"))
        p("jpeg_quality", 70)
        p("reconnect_sec", 2.0)
        p("available_modes", Parameter.Type.STRING_ARRAY, ParameterDescriptor(
            description="Sizes the camera offers (filled in when it opens; setting it does nothing)"))

        # Best effort, keep only the newest picture: an old picture is worse than none
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=1)
        self.pub_raw = self.create_publisher(Image, "image_raw", qos)
        self.pub_jpeg = self.create_publisher(CompressedImage, "image_raw/compressed", qos)
        self.pub_info = self.create_publisher(CameraInfo, "camera_info", qos)

        self._reopen = threading.Event()
        self._stop = threading.Event()
        self._frames = 0
        self.add_on_set_parameters_callback(self._on_params)
        self.add_post_set_parameters_callback(self._after_params)
        self.create_timer(5.0, self._report_fps)

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def param(self, name):
        return self.get_parameter(name).value

    def _on_params(self, params):
        for prm in params:
            if prm.name == "rotate" and prm.value not in ROTATIONS:
                return SetParametersResult(successful=False, reason="rotate must be 0, 90, 180 or 270")
            if prm.name == "flip" and prm.value not in FLIPS:
                return SetParametersResult(successful=False, reason="flip must be none, h, v or both")
            if prm.name == "jpeg_quality" and not 1 <= prm.value <= 100:
                return SetParametersResult(successful=False, reason="jpeg_quality must be 1-100")
        return SetParametersResult(successful=True)

    def _after_params(self, params):
        # Runs once the new values are stored, so the reopen sees them
        if any(prm.name in REOPEN_PARAMS for prm in params):
            self._reopen.set()

    def _open(self):
        src = parse_source(self.param("source"))
        cap = open_capture(src, self.param("width"), self.param("height"),
                           self.param("fps"), self.param("fourcc"))
        if cap is None:
            return None
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(f"opened {src} at {w}x{h}")
        if not is_network(src) and not is_file(src):
            dev = f"/dev/video{src}" if isinstance(src, int) else src
            modes = list_modes(dev, self.param("fourcc"))
            if modes:
                self.set_parameters([Parameter("available_modes", Parameter.Type.STRING_ARRAY, modes)])
        return cap

    def _capture_loop(self):
        cap = None
        while not self._stop.is_set():
            if cap is None or self._reopen.is_set():
                if cap is not None:
                    cap.release()
                self._reopen.clear()
                from_file = is_file(parse_source(self.param("source")))
                next_t = time.monotonic()
                cap = self._open()
                if cap is None:
                    self.get_logger().warn(
                        f"cannot open {self.param('source')}, retrying in {self.param('reconnect_sec')} s",
                        throttle_duration_sec=30.0)
                    time.sleep(self.param("reconnect_sec"))
                    continue

            if from_file:
                # A video file reads as fast as the disk allows: pace it like a real camera
                next_t = max(next_t + 1.0 / self.param("fps"), time.monotonic())
                time.sleep(max(0.0, next_t - time.monotonic()))
            ok, frame = cap.read()
            stamp = self.get_clock().now().to_msg()   # as close to the grab as we can get
            if not ok and from_file:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)    # end of the video: play it again
                continue
            if not ok:
                self.get_logger().warn("camera stopped sending pictures, reopening")
                cap.release()
                cap = None
                time.sleep(self.param("reconnect_sec"))
                continue

            frame = self._orient(frame)
            self._publish(frame, stamp)
            self._frames += 1

        if cap is not None:
            cap.release()

    def _orient(self, frame):
        rot = ROTATIONS.get(self.param("rotate"))
        if rot is not None:
            frame = cv2.rotate(frame, rot)
        flip = FLIPS.get(self.param("flip"))
        if flip is not None:
            frame = cv2.flip(frame, flip)
        return frame

    def _publish(self, frame, stamp):
        frame_id = self.param("frame_id")
        if self.pub_info.get_subscription_count() > 0:
            info = CameraInfo()
            info.header.stamp = stamp
            info.header.frame_id = frame_id
            info.height, info.width = frame.shape[:2]
            self.pub_info.publish(info)
        if self.param("publish_raw") and self.pub_raw.get_subscription_count() > 0:
            msg = Image()
            msg.header.stamp = stamp
            msg.header.frame_id = frame_id
            msg.height, msg.width = frame.shape[:2]
            msg.encoding = "bgr8"
            msg.step = msg.width * 3
            msg.data = frame.tobytes()
            self.pub_raw.publish(msg)
        if self.param("publish_compressed") and self.pub_jpeg.get_subscription_count() > 0:
            ok, jpeg = cv2.imencode(".jpg", frame,
                                    [cv2.IMWRITE_JPEG_QUALITY, self.param("jpeg_quality")])
            if ok:
                msg = CompressedImage()
                msg.header.stamp = stamp
                msg.header.frame_id = frame_id
                msg.format = "jpeg"
                msg.data = jpeg.tobytes()
                self.pub_jpeg.publish(msg)

    def _report_fps(self):
        fps, self._frames = self._frames / 5.0, 0
        self.get_logger().debug(f"{fps:.1f} fps")

    def destroy_node(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
        super().destroy_node()


def main():
    rclpy.init()
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
