# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The ROS-free decisions of the colour marker node (kept apart so they can be tested)."""

import json
import math

from r2_vision.color_marker import (bearing, color_warning, find_marker, match_fraction,
                                    model_from_pixel)


def wants_video(mode, preview, color_on_camera=False):
    """The camera only sends video while someone needs it (it is on_demand). When the camera
    finds the colour itself, following needs no video: only the console preview does."""
    return (mode == "follow" and not color_on_camera) or bool(preview)


def detect_value(old_mode, new_mode, detect_on_camera):
    """What to tell a dome camera that searches itself when the mode changes: 2 (look for the
    colour) on entering follow, 1 (back to faces) on leaving it, None for nothing (other camera
    kinds, or no change). See colour_on_camera_result for cameras that cannot find a colour."""
    if not detect_on_camera or (old_mode == "follow") == (new_mode == "follow"):
        return None
    return 2 if new_mode == "follow" else 1


def color_controls(model):
    """The camera's /control variables for a ColorModel, in the order to send them."""
    # whole numbers: modes.yaml may hold 12.0, and the camera only takes integers
    return [("color_h", int(model.h)), ("color_s", int(model.s)), ("color_v", int(model.v)),
            ("color_htol", int(round(model.hue_tol))), ("color_ltol", int(round(model.light_tol)))]


def colour_on_camera_result(responses):
    """responses: whether each color_controls variable was accepted. -> (the camera finds the
    colour itself, detect value to send). An ESP32-S3 camera does not know color_h: then the Pi
    follows the colour in its video as before, and the camera only pauses its faces (0)."""
    ok = bool(responses) and all(responses)
    return (True, 2) if ok else (False, 0)


def parse_pick(text):
    """/marker/pick JSON -> (x, y, hue_tol, light_tol) with x, y clamped to 0-1, or None."""
    try:
        d = json.loads(text)
        x, y = float(d["x"]), float(d["y"])
        hue_tol, light_tol = int(d["hue_tol"]), int(d["light_tol"])
    except (ValueError, KeyError, TypeError, OverflowError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return (min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0),
            min(max(hue_tol, 2), 40), min(max(light_tol, 10), 120))   # modes.yaml ranges


def pick_result(bgr, x, y, hue_tol, light_tol):
    """Colour under the fractions (x, y) of the picture, as the console shows it."""
    hh, ww = bgr.shape[:2]
    px, py = min(int(x * ww), ww - 1), min(int(y * hh), hh - 1)
    m = model_from_pixel(bgr, px, py, hue_tol, light_tol)
    found = find_marker(bgr, m, None)
    r, g, b = (int(c) for c in bgr[py, px][::-1])
    return {"h": m.h, "s": m.s, "v": m.v, "rgb": [r, g, b], "warning": color_warning(m),
            "match": match_fraction(bgr, m), "area": found.area if found else 0.0}


def marker_json(marker, hfov_deg, t):
    if marker is None:
        return json.dumps({"seen": False, "bearing": 0.0, "area": 0.0, "cx": 0.0, "cy": 0.0, "t": t})
    return json.dumps({"seen": True, "bearing": bearing(marker, hfov_deg), "area": marker.area,
                       "cx": marker.cx, "cy": marker.cy, "t": t})
