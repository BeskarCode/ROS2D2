# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The camera's colour search (components/r2_detect/color_detect.c), built on the PC and
compared with the Pi's (r2_vision/color_marker.py): both must find the same blob."""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "ros2_ws", "src", "r2_vision"))
sys.path.insert(0, HERE)

from cbuild import build, run   # noqa: E402
from r2_vision.color_marker import ColorModel, Marker, find_marker   # noqa: E402

W, H = 320, 240
GREY = (128, 128, 128)


def canvas():
    return np.full((H, W, 3), GREY, np.uint8)


def hsv_bgr(h, s, v):
    import cv2
    return tuple(int(c) for c in cv2.cvtColor(np.uint8([[[h, s, v]]]), cv2.COLOR_HSV2BGR)[0, 0])


def blob(img, x0, y0, x1, y1, bgr):
    img[y0:y1, x0:x1] = bgr


def case(name):
    img = canvas()
    prev = None
    if name == "blue":
        m = ColorModel(110, 200, 200, 10, 60)
        blob(img, 200, 50, 260, 120, hsv_bgr(110, 200, 200))
    elif name == "red_wrap":
        m = ColorModel(2, 200, 200, 10, 60)
        blob(img, 40, 100, 100, 180, hsv_bgr(178, 200, 200))
    elif name == "pale_no_match":
        m = ColorModel(60, 200, 200, 10, 40)
        blob(img, 100, 100, 180, 180, hsv_bgr(60, 60, 200))
    elif name == "two_blobs_no_prev":
        m = ColorModel(30, 220, 220, 8, 50)
        blob(img, 10, 10, 50, 50, hsv_bgr(30, 220, 220))
        blob(img, 200, 120, 300, 220, hsv_bgr(30, 220, 220))
    elif name == "two_blobs_prev_near_small":
        m = ColorModel(30, 220, 220, 8, 50)
        blob(img, 10, 10, 50, 50, hsv_bgr(30, 220, 220))
        blob(img, 200, 120, 300, 220, hsv_bgr(30, 220, 220))
        prev = Marker(0.1, 0.1, 0.02)
    elif name == "too_small":
        m = ColorModel(110, 200, 200, 10, 60)
        blob(img, 100, 100, 112, 112, hsv_bgr(110, 200, 200))   # 144 px = 0.19 %
    return img, m, prev


CASES = ["blue", "red_wrap", "pale_no_match", "two_blobs_no_prev", "two_blobs_prev_near_small",
         "too_small"]


@pytest.fixture(scope="module")
def cli(tmp_path_factory):
    return build(tmp_path_factory.mktemp("c"), "color_cli", ["color_cli.c", "../components/r2_detect/color_detect.c"])


def c_find(cli, tmp_path, bgr, m, prev, step):
    raw = tmp_path / "img.rgb"
    raw.write_bytes(np.ascontiguousarray(bgr[:, :, ::-1]).tobytes())
    args = [str(raw), W, H, m.h, m.s, m.v, m.hue_tol, m.light_tol, step]
    if prev:
        args += [prev.cx, prev.cy, prev.area]
    seen, cx, cy, area = run(cli, args).split()
    return seen == "1", float(cx), float(cy), float(area)


@pytest.mark.parametrize("step", [1, 2])
@pytest.mark.parametrize("name", CASES)
def test_same_blob_as_the_pi(cli, tmp_path, name, step):
    img, m, prev = case(name)
    want = find_marker(img, m, prev)
    seen, cx, cy, area = c_find(cli, tmp_path, img, m, prev, step)
    assert seen == (want is not None)
    if want is not None:
        assert abs(cx - want.cx) < 0.02
        assert abs(cy - want.cy) < 0.02
        assert abs(area - want.area) < 0.15 * want.area


def test_expected_answers(cli, tmp_path):
    """Not only the same as the Pi: the right answer (so a bug in both cannot hide)."""
    assert c_find(cli, tmp_path, *case("too_small")[:3], 1)[0] is False
    assert c_find(cli, tmp_path, *case("pale_no_match")[:3], 1)[0] is False
    seen, cx, cy, _ = c_find(cli, tmp_path, *case("red_wrap")[:3], 1)
    assert seen and abs(cx - 70 / W) < 0.01 and abs(cy - 140 / H) < 0.01
    seen, cx, _, _ = c_find(cli, tmp_path, *case("two_blobs_no_prev")[:3], 1)
    assert seen and cx > 0.5
    seen, cx, _, _ = c_find(cli, tmp_path, *case("two_blobs_prev_near_small")[:3], 1)
    assert seen and cx < 0.5


def test_model_ranges(cli):
    assert run(cli, ["--valid", 0, 0, 0, 2, 10]).strip() == "1"
    assert run(cli, ["--valid", 179, 255, 255, 40, 120]).strip() == "1"
    assert run(cli, ["--valid", 180, 0, 0, 10, 10]).strip() == "0"
    assert run(cli, ["--valid", 10, 0, 0, 41, 10]).strip() == "0"
    assert run(cli, ["--valid", 10, 0, 0, 10, 9]).strip() == "0"
