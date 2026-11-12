# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The commands to a dome camera that searches itself go out one at a time, in order."""
import threading
import time

from r2_vision.camera_commands import CameraCommander, marker_stale
from r2_vision.color_marker import ColorModel

MODEL = ColorModel(5, 200, 180, 12, 70)


class FakeCamera:
    def __init__(self, delay=0.0, rejects_colour=False):
        self.calls, self.delay, self.rejects = [], delay, rejects_colour
        self.lock = threading.Lock()

    def send(self, camera, var, val):
        time.sleep(self.delay)
        with self.lock:
            self.calls.append((var, val))
        return not (self.rejects and var.startswith("color_"))

    def detect_values(self):
        return [v for k, v in self.calls if k == "detect"]


def run(cam, actions):
    results = []
    c = CameraCommander(cam.send, lambda camera, on: results.append(on))
    for a in actions:
        a(c)
    c.wait_idle()
    c.stop()
    return results


def test_follow_gives_the_colour_then_detect_2():
    cam = FakeCamera()
    assert run(cam, [lambda c: c.follow("cam2", MODEL)]) == [True]
    assert cam.calls == [("color_h", 5), ("color_s", 200), ("color_v", 180), ("color_htol", 12),
                         ("color_ltol", 70), ("detect", 2)]


def test_camera_that_rejects_the_colour_only_pauses_faces():
    cam = FakeCamera(rejects_colour=True)
    assert run(cam, [lambda c: c.follow("cam2", MODEL)]) == [False]
    assert cam.calls == [("color_h", 5), ("detect", 0)]   # stops at the first refusal


def test_leaving_while_a_slow_camera_takes_the_colour_ends_in_faces():
    cam = FakeCamera(delay=0.05)
    results = run(cam, [lambda c: c.follow("cam2", MODEL), lambda c: c.leave("cam2")])
    assert cam.detect_values()[-1] == 1
    assert results == []   # the follow that was left never switches the Pi to the camera's blob


def test_leave_then_follow_again_ends_in_colour():
    cam = FakeCamera(delay=0.02)
    results = run(cam, [lambda c: c.follow("cam2", MODEL), lambda c: c.leave("cam2"),
                        lambda c: c.follow("cam2", MODEL)])
    assert cam.detect_values()[-1] == 2
    assert results[-1] is True


def test_float_tolerances_are_sent_as_integers():
    cam = FakeCamera()
    run(cam, [lambda c: c.follow("cam2", ColorModel(5, 200, 180, 12.0, 70.0))])
    assert ("color_htol", 12) in cam.calls and ("color_ltol", 70) in cam.calls
    assert all(isinstance(v, int) for _, v in cam.calls)


def test_marker_stale():
    assert not marker_stale(10.0, 11.5)
    assert marker_stale(10.0, 12.5)
    assert marker_stale(None, 12.5)
