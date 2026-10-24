"""R2 face detector node: one instance per camera.

Finds faces with OpenCV's YuNet detector (the same one the proof of concept used)
and publishes them as standard ROS detections. Each detection list keeps the
stamp of the picture it came from, so the dome controller knows how old it is.

Topics (relative to the node, e.g. /cameras/front/...):
  in   image_raw                     sensor_msgs/Image
  out  faces                         vision_msgs/Detection2DArray  (pixels of the full picture,
                                                                   biggest face first)
  out  faces/image/compressed        sensor_msgs/CompressedImage   picture with the boxes drawn,
                                                                   only when someone watches it

Needs OpenCV >= 4.8 for the 2023 YuNet model.
"""

import os
import time

import cv2
import rclpy
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage, Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from r2_vision.image_utils import biggest, image_to_bgr

# Changing one of these rebuilds the detector
REBUILD_PARAMS = {"model", "detect_width", "score_threshold", "nms_threshold", "top_k"}


def default_model():
    return os.path.join(get_package_share_directory("r2_vision"), "models",
                        "face_detection_yunet_2023mar.onnx")


class FaceDetectorNode(Node):
    def __init__(self):
        super().__init__("face_detector")
        p = self.declare_parameter
        p("model", default_model(), ParameterDescriptor(description="YuNet .onnx model"))
        p("detect_width", 320, ParameterDescriptor(
            description="Picture width the detector works at: smaller = faster, shorter range "
                        "(320 gave 25 fps on a Pi 4 in the proof of concept)"))
        p("score_threshold", 0.6, ParameterDescriptor(description="0-1, higher = fewer false faces"))
        p("nms_threshold", 0.3)
        p("top_k", 50)
        p("jpeg_quality", 60)

        major, minor = (int(v) for v in cv2.__version__.split(".")[:2])
        if (major, minor) < (4, 8):
            self.get_logger().error(
                f"OpenCV {cv2.__version__} is too old for YuNet 2023 (needs >= 4.8). "
                "Build the workspace with ~/r2-venv activated.")

        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=1)
        self.pub_faces = self.create_publisher(Detection2DArray, "faces", 10)
        self.pub_debug = self.create_publisher(CompressedImage, "faces/image/compressed", qos)
        self.create_subscription(Image, "image_raw", self._on_image, qos)

        self._detector = None
        self._det_size = None
        self._times = []
        self.add_post_set_parameters_callback(self._after_params)
        self.create_timer(5.0, self._report)

    def param(self, name):
        return self.get_parameter(name).value

    def _after_params(self, params):
        if any(prm.name in REBUILD_PARAMS for prm in params):
            self._detector = None

    def _detector_for(self, w, h):
        det_w = min(self.param("detect_width"), w)
        det_h = int(round(h * det_w / w))
        if self._detector is None or self._det_size != (det_w, det_h):
            self._detector = cv2.FaceDetectorYN.create(
                self.param("model"), "", (det_w, det_h),
                self.param("score_threshold"), self.param("nms_threshold"), self.param("top_k"))
            self._det_size = (det_w, det_h)
            self.get_logger().info(f"detecting at {det_w}x{det_h} on {w}x{h} pictures")
        return self._detector, det_w, det_h

    def _on_image(self, msg):
        t0 = time.perf_counter()
        frame = image_to_bgr(msg)
        if frame is None or frame.ndim != 3:
            self.get_logger().warn(f"unsupported encoding {msg.encoding}", throttle_duration_sec=30.0)
            return
        h, w = frame.shape[:2]
        detector, det_w, det_h = self._detector_for(w, h)

        # Detect on a smaller copy (4x faster on a Pi 4), boxes scaled back to the full picture
        small = cv2.resize(frame, (det_w, det_h)) if det_w != w else frame
        _, faces = detector.detect(small)
        if faces is not None:
            faces[:, :14] *= w / det_w      # box + 5 landmarks are pixels; [14] is the score
            first = biggest(faces)
            order = [first] + [i for i in range(len(faces)) if i != first]
            faces = faces[order]

        out = Detection2DArray()
        out.header = msg.header             # same stamp and frame as the picture
        for f in (faces if faces is not None else []):
            x, y, fw, fh, score = float(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[14])
            det = Detection2D()
            det.header = msg.header
            det.bbox.center.position.x = x + fw / 2
            det.bbox.center.position.y = y + fh / 2
            det.bbox.size_x = fw
            det.bbox.size_y = fh
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = "face"
            hyp.hypothesis.score = score
            det.results.append(hyp)
            out.detections.append(det)
        self.pub_faces.publish(out)
        self._times.append(time.perf_counter() - t0)

        if self.pub_debug.get_subscription_count() > 0:
            self._publish_debug(frame, faces, msg.header)

    def _publish_debug(self, frame, faces, header):
        img = frame.copy()
        for i, f in enumerate(faces if faces is not None else []):
            x, y, fw, fh = (int(v) for v in f[:4])
            colour = (0, 255, 0) if i == 0 else (0, 200, 255)   # green = the one R2 looks at
            cv2.rectangle(img, (x, y), (x + fw, y + fh), colour, 2)
            cv2.putText(img, f"{f[14]:.2f}", (x, max(y - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
        ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.param("jpeg_quality")])
        if ok:
            msg = CompressedImage()
            msg.header = header
            msg.format = "jpeg"
            msg.data = jpeg.tobytes()
            self.pub_debug.publish(msg)

    def _report(self):
        if self._times:
            avg = 1000 * sum(self._times) / len(self._times)
            self.get_logger().debug(f"{len(self._times) / 5.0:.1f} fps, {avg:.0f} ms per picture")
        self._times = []


def main():
    rclpy.init()
    node = FaceDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
