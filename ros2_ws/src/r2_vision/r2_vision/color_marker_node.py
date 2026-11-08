# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 colour marker node: camera picture -> /marker, for the follow-a-colour mode.

Topics:
  in   /cameras/<follow.camera>/image_raw   sensor_msgs/Image  only while /r2/mode is follow or
                                                              the console is previewing
  in   /r2/mode                             std_msgs/String
  in   /r2/modes/reload                     std_msgs/Empty     modes.yaml was saved: read it again
  in   /marker/preview                      std_msgs/Bool      Setup -> Modes -> Follow is open
  in   /marker/pick                         std_msgs/String    {"x","y","hue_tol","light_tol"}
  in   /cameras/<follow.camera>/marker_raw  std_msgs/String    while following with a camera that finds
                                                              the colour itself (detect: camera)
  out  /marker/pick_result                  std_msgs/String    {"h","s","v","rgb","warning","match","area"}
  out  /marker                              std_msgs/String    {"seen","bearing","area","cx","cy","t"}
  out  /marker/mask/compressed              sensor_msgs/CompressedImage  matches painted, preview only

A dome camera that searches itself (detect: camera) is told the colour and detect=2 when follow
starts, so it looks for the colour instead of faces and sends only where it is (marker_raw, no
video); it gets detect=1 (faces) back when follow ends. Its video is then only for the console's
preview. Other cameras (detect: pi) send pictures and the colour is searched here.
"""

import json
import os
import threading
import urllib.request

import cv2
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import Bool, Empty, String

from r2_camera.config import config_path, load_cameras
from r2_nav.modes import load_modes, modes_path
from r2_vision.color_marker import ColorModel, find_marker, match_mask
from r2_vision.image_utils import image_to_bgr
from r2_vision.marker_logic import (color_controls, detect_value, marker_from_raw, marker_json, parse_pick,
                                    pick_result, wants_video)
from r2_vision.remote_faces import control_url, faces_url

MASK_PERIOD = 0.2   # at most 5 mask pictures per second


class ColorMarkerNode(Node):
    def __init__(self):
        super().__init__("color_marker")
        self.declare_parameter("modes_config", "")
        self.declare_parameter("cameras_config", "")
        self.declare_parameter("jpeg_quality", 60)
        self._video_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                     history=HistoryPolicy.KEEP_LAST, depth=1)
        latched = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             history=HistoryPolicy.KEEP_LAST, depth=1)
        self.mode = ""
        self.preview = False
        self.follow = None           # the follow section of modes.yaml
        self.cameras = {}
        self.camera = None           # name of the camera we use
        self._sub = None
        self._sub_camera = None
        self._raw_sub = None         # marker_raw of a camera that finds the colour itself
        self._raw_camera = None
        self._last = None            # last picture (BGR)
        self._prev = None            # last Marker, to keep the same blob
        self._last_mask = 0.0
        self._model = None
        self.pub_marker = self.create_publisher(String, "/marker", 10)
        self.pub_result = self.create_publisher(String, "/marker/pick_result", 10)
        self.pub_mask = self.create_publisher(CompressedImage, "/marker/mask/compressed", self._video_qos)
        self.create_subscription(String, "/r2/mode", self._on_mode, latched)
        self.create_subscription(Empty, "/r2/modes/reload", lambda _m: self._reload(), 10)
        self.create_subscription(Bool, "/marker/preview", self._on_preview, 10)
        self.create_subscription(String, "/marker/pick", self._on_pick, 10)
        self._reload()

    def _reload(self):
        """Read modes.yaml and cameras.yaml; on any problem log it and keep what we had."""
        try:
            path = self.get_parameter("modes_config").value
            if not path:
                path = modes_path(os.path.join(get_package_share_directory("r2_nav"), "config", "modes.yaml"))
            self.follow = load_modes(path)["follow"]
        except Exception as e:
            self.get_logger().error(f"modes.yaml: {e}")
        try:
            path = self.get_parameter("cameras_config").value
            if not path:
                path = config_path(os.path.join(get_package_share_directory("r2_camera"), "config", "cameras.yaml"))
            self.cameras = load_cameras(path)
        except Exception as e:
            self.get_logger().error(f"cameras.yaml: {e}")
        f = self.follow
        c = f["color"] if f else None
        self._model = ColorModel(c["h"], c["s"], c["v"], f["hue_tol"], f["light_tol"]) if c else None
        self._prev = None
        self._update_subscription()
        if self.mode == "follow" and self._color_on_camera() and self._model is not None:
            self._tell_async(self.camera, color_controls(self._model))   # the new colour, while following

    def _cam_params(self):
        return self.cameras.get(self.camera, {})

    def _color_on_camera(self, camera=None):
        name = camera or (self.follow["camera"] if self.follow else None)
        return self.cameras.get(name, {}).get("detect") == "camera"

    def _update_subscription(self):
        name = self.follow["camera"] if self.follow else None
        on_camera = self._color_on_camera(name)
        want = name is not None and wants_video(self.mode, self.preview, on_camera)
        want_raw = name is not None and on_camera and self.mode == "follow"
        if self._raw_sub is not None and (not want_raw or name != self._raw_camera):
            self.destroy_subscription(self._raw_sub)
            self._raw_sub = None
            self._raw_camera = None
        if want_raw and self._raw_sub is None:
            self._raw_sub = self.create_subscription(String, f"/cameras/{name}/marker_raw", self._on_raw, 10)
            self._raw_camera = name
        if self._sub is not None and (not want or name != self._sub_camera):
            self.destroy_subscription(self._sub)
            self._sub = None
            self._sub_camera = None
        self.camera = name
        if want and self._sub is None:
            self._sub = self.create_subscription(Image, f"/cameras/{name}/image_raw", self._on_image,
                                                 self._video_qos)
            self._sub_camera = name
        if not want:
            self._last = None

    def _on_mode(self, msg):
        old, self.mode = self.mode, msg.data
        self._prev = None
        v = detect_value(old, self.mode, self._color_on_camera())
        if v == 2 and self._model is not None:
            # the colour first, then switch the camera from faces to it
            self._tell_async(self.camera, color_controls(self._model) + [("detect", 2)])
        elif v is not None:
            self._tell_async(self.camera, [("detect", v)])
        self._update_subscription()

    def _on_preview(self, msg):
        self.preview = bool(msg.data)
        self._update_subscription()

    def _tell_async(self, camera, settings):
        threading.Thread(target=self._tell, args=(camera, settings), daemon=True).start()

    def _tell(self, camera, settings):
        """Sets the camera's /control values, in order; stops at the first that fails."""
        params = self.cameras.get(camera, {})
        base = params.get("faces_url") or faces_url(str(params.get("source", "")))
        for var, val in settings:
            try:
                with urllib.request.urlopen(control_url(base, var, val), timeout=3.0) as r:
                    r.read()
            except Exception as e:   # the camera is off or too old: only worth a line
                self.get_logger().warning(f"could not set {var}={val} on {camera} ({e})")
                return

    def _on_pick(self, msg):
        pick = parse_pick(msg.data)
        if pick is None:
            self.get_logger().warning("bad /marker/pick")
            return
        if self._last is None:
            self.get_logger().warning("/marker/pick: no picture yet (is /marker/preview on?)")
            return
        out = String()
        out.data = json.dumps(pick_result(self._last, *pick))
        self.pub_result.publish(out)

    def _on_image(self, msg):
        frame = image_to_bgr(msg)
        if frame is None or frame.ndim != 3:
            return
        self._last = frame
        now = self.get_clock().now().nanoseconds / 1e9
        hfov = float(self._cam_params().get("hfov_deg", 60.0))
        marker = None
        if self._model is not None and (self.mode == "follow" or self.preview):
            marker = find_marker(frame, self._model, self._prev if self.mode == "follow" else None)
        if self.mode == "follow" and not self._color_on_camera():   # else the camera says where it is
            self._prev = marker
            out = String()
            out.data = marker_json(marker, hfov, now)
            self.pub_marker.publish(out)
        if self.preview and self._model is not None and now - self._last_mask >= MASK_PERIOD:
            self._last_mask = now
            self._publish_mask(frame, msg.header)

    def _on_raw(self, msg):
        """Where the camera found the colour itself (detect=2) -> /marker, as from a picture."""
        if self.mode != "follow":
            return
        out = String()
        out.data = marker_json(marker_from_raw(msg.data), float(self._cam_params().get("hfov_deg", 60.0)),
                               self.get_clock().now().nanoseconds / 1e9)
        self.pub_marker.publish(out)

    def _publish_mask(self, frame, header):
        img = frame.copy()
        img[match_mask(frame, self._model) > 0] = (255, 0, 255)
        ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.get_parameter("jpeg_quality").value])
        if ok:
            out = CompressedImage()
            out.header = header
            out.format = "jpeg"
            out.data = jpeg.tobytes()
            self.pub_mask.publish(out)


def main():
    rclpy.init()
    node = ColorMarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
