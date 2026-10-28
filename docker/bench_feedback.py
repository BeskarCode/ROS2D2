# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Tells the webcam test page what the bench sees while you move.

    python3 bench_feedback.py <state url> <seconds>

Posts phase "move", the seconds left, whether a face is seen and the dome speed,
five times a second, until the time is up or Stop is pressed on the page.
"""

import json
import sys
import time
import urllib.request

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int16
from vision_msgs.msg import Detection2DArray


def get(url):
    try:
        return json.load(urllib.request.urlopen(url, timeout=0.5))
    except (OSError, ValueError):
        return {}


def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(),
                                 {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=0.5)
    except OSError:
        pass   # the page is only a convenience; never stop the test for it


class Feedback(Node):
    def __init__(self, url, seconds):
        super().__init__("bench_feedback")
        self.url = url
        self.end = time.monotonic() + seconds
        self.speed = None
        self.face_at = 0.0
        self.create_subscription(Int16, "/dome/speed_cmd", self._on_speed, 10)
        self.create_subscription(Detection2DArray, "/cameras/front/faces", self._on_faces, 10)
        self.create_timer(0.2, self._tick)

    def _on_speed(self, msg):
        self.speed = msg.data

    def _on_faces(self, msg):
        if msg.detections:
            self.face_at = time.monotonic()

    def _tick(self):
        now = time.monotonic()
        post(self.url, {"phase": "move", "remaining": max(0.0, self.end - now),
                        "speed": self.speed, "face": now - self.face_at < 0.5})
        if now >= self.end or get(self.url).get("stop"):
            raise SystemExit


def main():
    rclpy.init()
    node = Feedback(sys.argv[1], float(sys.argv[2]))
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
