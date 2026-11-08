# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""color_detect.cpp (the dome camera's colour search) against r2_vision's find_marker (the Pi's).

Builds test/color_cli.cpp with a C++ compiler on the PC (g++, or `python -m ziglang c++`) and runs
both on the same synthetic pictures. Skipped when there is no compiler.
    python -m pytest firmware/r2_domecam/test
"""

import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FW, "..", "..", "ros2_ws", "src", "r2_vision"))
from r2_vision.color_marker import ColorModel, Marker, find_marker  # noqa: E402

W, H = 320, 240


def _compiler():
    if shutil.which("g++"):
        return ["g++"]
    try:
        subprocess.run([sys.executable, "-m", "ziglang", "c++", "--version"], capture_output=True, check=True)
        return [sys.executable, "-m", "ziglang", "c++"]
    except Exception:
        return None


@pytest.fixture(scope="module")
def cli():
    cxx = _compiler()
    if cxx is None:
        pytest.skip("no C++ compiler on this machine")
    out = os.path.join(tempfile.mkdtemp(), "color_cli" + (".exe" if os.name == "nt" else ""))
    subprocess.run(cxx + ["-O2", "-std=c++17", "-I", FW, os.path.join(HERE, "color_cli.cpp"),
                          os.path.join(FW, "color_detect.cpp"), "-o", out], check=True)
    return out


def model_of(bgr, hue_tol=10, light_tol=60):
    h, s, v = (int(c) for c in cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0, 0])
    return ColorModel(h, s, v, hue_tol, light_tol)


def picture(*rects):
    """Grey picture with filled rectangles: (x, y, w, h, bgr)."""
    img = np.full((H, W, 3), 128, np.uint8)
    for x, y, w, h, bgr in rects:
        img[y:y + h, x:x + w] = bgr
    return img


def run_cli(cli, bgr, m, prev=None):
    path = os.path.join(tempfile.mkdtemp(), "pic.rgb")
    with open(path, "wb") as f:
        f.write(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).tobytes())   # the camera decodes to R,G,B
    args = [cli, path, str(W), str(H), str(m.h), str(m.s), str(m.v), str(m.hue_tol), str(m.light_tol)]
    if prev is not None:
        args += [str(prev.cx), str(prev.cy), str(prev.area)]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout.split()
    seen = out[0] == "1"
    return Marker(float(out[1]), float(out[2]), float(out[3])) if seen else None


def same(cam, pi):
    assert (cam is None) == (pi is None), (cam, pi)
    if pi is not None:
        assert abs(cam.cx - pi.cx) < 0.02 and abs(cam.cy - pi.cy) < 0.02, (cam, pi)
        assert abs(cam.area - pi.area) / pi.area < 0.15, (cam, pi)


BLUE = (200, 60, 20)          # BGR


def test_one_blue_blob(cli):
    img = picture((100, 80, 60, 40, BLUE))
    m = model_of(BLUE)
    same(run_cli(cli, img, m), find_marker(img, m, None))
    assert find_marker(img, m, None) is not None


def test_red_wraps_round_hue_zero(cli):
    # one blob whose left half has hue ~2 and right half hue ~177: both match a red at hue 2
    img = picture((60, 60, 40, 60, (0, 8, 210)), (100, 60, 40, 60, (12, 0, 210)))
    m = model_of((0, 8, 210))
    pi = find_marker(img, m, None)
    same(run_cli(cli, img, m), pi)
    assert pi is not None and pi.area > 0.06   # the two halves are one blob


def test_pale_colour_does_not_match_a_strong_one(cli):
    img = picture((100, 80, 60, 40, (140, 140, 150)))
    m = model_of(BLUE)
    same(run_cli(cli, img, m), find_marker(img, m, None))
    assert find_marker(img, m, None) is None


def test_two_blobs_without_previous_takes_the_biggest(cli):
    img = picture((20, 20, 80, 60, BLUE), (220, 150, 40, 30, BLUE))
    m = model_of(BLUE)
    pi = find_marker(img, m, None)
    same(run_cli(cli, img, m), pi)
    assert pi.cx < 0.5


def test_two_blobs_with_previous_takes_the_nearest(cli):
    img = picture((20, 20, 80, 60, BLUE), (220, 150, 40, 30, BLUE))
    m = model_of(BLUE)
    prev = Marker(0.75, 0.68, 0.02)
    pi = find_marker(img, m, prev)
    same(run_cli(cli, img, m, prev), pi)
    assert pi.cx > 0.5


def test_too_small_blob_is_not_a_marker(cli):
    img = picture((150, 110, 10, 15, BLUE))     # 150 px of 76800: 0.2 %
    m = model_of(BLUE)
    same(run_cli(cli, img, m), find_marker(img, m, None))
    assert find_marker(img, m, None) is None
