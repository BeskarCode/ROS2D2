# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Commands to a dome camera that searches itself, one at a time and in order (ROS-free).

Entering and leaving follow each send HTTP requests that can take seconds on a weak WiFi. Sent
from separate threads they could reach the camera out of order and leave it looking for the
colour while R2 is not following (or the other way round). Here a single worker sends them in
the order they were asked for, and a follow that was left meanwhile ends with detect=1.
"""

import queue
import threading

from r2_vision.marker_logic import color_controls, colour_on_camera_result

STALE_SEC = 2.0   # the camera sends a line per picture (several a second), even when unseen


def marker_stale(last_t, now, timeout=STALE_SEC):
    """True when the camera's blob has not arrived for `timeout` seconds (it rebooted into faces,
    or the WiFi dropped): then follow the colour in the video and ask the camera again."""
    return last_t is None or now - last_t > timeout


class CameraCommander:
    """send(camera, var, val) -> bool does one /control request.
    on_result(camera, on_camera) is called after a follow that is still wanted: on_camera says
    whether the camera now finds the colour itself (else the colour is found in its video)."""

    def __init__(self, send, on_result):
        self._send = send
        self._on_result = on_result
        self._want = {}                 # camera -> "follow" or "faces"
        self._lock = threading.Lock()
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def follow(self, camera, model):
        with self._lock:
            self._want[camera] = "follow"
        self._q.put(("follow", camera, model))

    def leave(self, camera):
        with self._lock:
            self._want[camera] = "faces"
        self._q.put(("leave", camera, None))

    def idle(self):
        return self._q.unfinished_tasks == 0

    def wait_idle(self):
        self._q.join()

    def stop(self):
        self._q.put(None)

    def _wanted(self, camera):
        with self._lock:
            return self._want.get(camera)

    def _run(self):
        while True:
            job = self._q.get()
            try:
                if job is None:
                    return
                kind, camera, model = job
                if kind == "leave":
                    self._send(camera, "detect", 1)
                elif self._wanted(camera) == "follow":   # skip a follow already left
                    self._do_follow(camera, model)
            finally:
                self._q.task_done()

    def _do_follow(self, camera, model):
        oks = []
        for var, val in color_controls(model) if model else []:
            oks.append(self._send(camera, var, val))
            if not oks[-1]:   # an ESP32-S3 refuses the first one: no need to try the rest
                break
        on_camera, detect = colour_on_camera_result(oks if all(oks) and len(oks) == 5 else oks + [False])
        if not self._send(camera, "detect", detect):
            on_camera = False
        if self._wanted(camera) != "follow":   # left while this was going on
            self._send(camera, "detect", 1)
            return
        self._on_result(camera, on_camera)
