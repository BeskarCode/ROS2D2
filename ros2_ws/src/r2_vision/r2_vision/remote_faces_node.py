# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 remote faces node: for a camera that finds the faces itself (r2_domecam on an ESP32-S3).

Takes the place of the face detector for that camera: instead of searching every picture
on the Pi, it reads the faces the camera already found (http://<camera>:82/faces, a few
numbers per picture) and publishes them exactly like the face detector does, so the dome
tracker and the web console do not notice the difference.

Topics (relative to the node, e.g. /cameras/cam2/...):
  out  faces                         vision_msgs/Detection2DArray  (pixels of the turned
                                                                   picture, biggest face first)
  out  faces/image/compressed        sensor_msgs/CompressedImage   the camera picture with the
                                                                   boxes drawn, only when watched
  out  marker_raw                    std_msgs/String               {"seen","cx","cy","area","lat_ms"}
                                                                   while the camera searches the
                                                                   follow colour (detect=2)
  in   image_raw                     sensor_msgs/Image             only while someone watches
"""

import threading
import urllib.request

import cv2
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from r2_vision.image_utils import image_to_bgr, pixelate
from r2_vision.remote_faces import control_url, iter_lines, marker_raw, orient_box, parse_line


class RemoteFacesNode(Node):
    def __init__(self):
        super().__init__("face_detector")
        p = self.declare_parameter
        p("url", "")
        p("rotate", 0)            # the same rotate and flip as the camera node of this camera
        p("flip", "none")
        p("frame_id", "camera")
        p("reconnect_sec", 2.0)
        p("jpeg_quality", 60)
        p("pixelate", False)

        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=1)
        self._qos = qos
        self.pub_faces = self.create_publisher(Detection2DArray, "faces", 10)
        self.pub_debug = self.create_publisher(CompressedImage, "faces/image/compressed", qos)
        self.pub_marker = self.create_publisher(String, "marker_raw", 10)
        self._image_sub = None
        self._latest = None           # (faces in the turned picture, its width, height)
        self._count = 0
        self.create_timer(1.0, self._watch_debug)
        self.create_timer(5.0, self._report)

        # rotate is decided here (cameras.yaml, or live from the web console): the camera is
        # told to turn its picture the same way, so its detector sees the faces upright
        self.add_post_set_parameters_callback(self._after_params)

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self.get_logger().info(f"faces found on the camera: {self.param('url')}")

    def param(self, name):
        return self.get_parameter(name).value

    def _read_loop(self):
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(self.param("url"), timeout=5.0) as stream:
                    self.get_logger().info("receiving faces from the camera")
                    self._tell_rotate()
                    for line in iter_lines(stream):
                        if self._stop.is_set():
                            return
                        self._on_line(line)
            except Exception as e:   # camera off, WiFi gone, busy...: keep trying
                self.get_logger().warning(f"no faces from {self.param('url')} ({e}), retrying",
                                          throttle_duration_sec=30.0)
            self._stop.wait(self.param("reconnect_sec"))

    def _after_params(self, params):
        if any(prm.name == "rotate" for prm in params):
            threading.Thread(target=self._tell_rotate, daemon=True).start()

    def _tell_rotate(self):
        url = control_url(self.param("url"), "rotate", self.param("rotate") % 360)
        try:
            with urllib.request.urlopen(url, timeout=3.0) as r:
                r.read()
        except Exception as e:   # an older camera without rotate: the boxes are turned here
            self.get_logger().warning(f"could not set the camera's rotate ({e})")

    def _on_line(self, line):
        d = parse_line(line)
        if d is None:
            return
        rotate = (self.param("rotate") - d["rot"]) % 360   # what the camera has not turned yet
        if d["mode"] == "color":
            # Searching the follow colour instead of faces (detect=2): only where the colour is
            out_m = String()
            out_m.data = marker_raw(d, rotate, self.param("flip"))
            self.pub_marker.publish(out_m)
            self._count += 1
            return
        # The camera says how old the picture is: stamp it with when it was taken
        stamp = (self.get_clock().now() - Duration(nanoseconds=int(d["lat_ms"] * 1e6))).to_msg()
        out = Detection2DArray()
        out.header.stamp = stamp
        out.header.frame_id = self.param("frame_id")
        turned = []
        width, height = d["w"], d["h"]
        for x, y, w, h, score in d["faces"]:
            x, y, w, h, width, height = orient_box(x, y, w, h, d["w"], d["h"], rotate, self.param("flip"))
            turned.append((x, y, w, h, score))
            det = Detection2D()
            det.header = out.header
            det.bbox.center.position.x = x + w / 2
            det.bbox.center.position.y = y + h / 2
            det.bbox.size_x = w
            det.bbox.size_y = h
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = "face"
            hyp.hypothesis.score = score
            det.results.append(hyp)
            out.detections.append(det)
        if not d["faces"]:
            width, height = orient_box(0, 0, 0, 0, d["w"], d["h"], rotate)[4:]
        self.pub_faces.publish(out)
        self._latest = (turned, width, height)
        self._count += 1

    # ---- the picture with the boxes, for the web console: only while someone watches it

    def _watch_debug(self):
        watched = self.pub_debug.get_subscription_count() > 0
        if watched and self._image_sub is None:
            self._image_sub = self.create_subscription(Image, "image_raw", self._on_image, self._qos)
        elif not watched and self._image_sub is not None:
            self.destroy_subscription(self._image_sub)
            self._image_sub = None

    def _on_image(self, msg):
        frame = image_to_bgr(msg)
        if frame is None or self._latest is None:
            return
        faces, fw, fh = self._latest
        sx, sy = frame.shape[1] / fw, frame.shape[0] / fh
        img = frame.copy()
        for i, (x, y, w, h, score) in enumerate(faces):
            x, y, w, h = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
            if self.param("pixelate"):
                pixelate(img, x, y, w, h)
            colour = (0, 255, 0) if i == 0 else (0, 200, 255)   # green = the one R2 looks at
            cv2.rectangle(img, (x, y), (x + w, y + h), colour, 2)
            cv2.putText(img, f"{score:.2f}", (x, max(y - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
        ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.param("jpeg_quality")])
        if ok:
            out = CompressedImage()
            out.header = msg.header
            out.format = "jpeg"
            out.data = jpeg.tobytes()
            self.pub_debug.publish(out)

    def _report(self):
        self.get_logger().debug(f"{self._count / 5.0:.1f} face messages per second")
        self._count = 0

    def destroy_node(self):
        self._stop.set()
        super().destroy_node()


def main():
    rclpy.init()
    node = RemoteFacesNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
