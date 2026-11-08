# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The ROS-free decisions of the colour marker node (kept apart so they can be tested)."""

import json
import math

from r2_vision.color_marker import (Marker, bearing, color_warning, find_marker, match_fraction,
                                    model_from_pixel)


def wants_video(mode, preview, color_on_camera=False):
    """The camera only sends video while someone needs it (it is on_demand). A camera that finds
    the colour itself (detect: camera) sends where the colour is instead: then only the console's
    preview needs its video."""
    return bool(preview) or (mode == "follow" and not color_on_camera)


def detect_value(old_mode, new_mode, detect_on_camera):
    """What to tell a dome camera that searches itself (detect: camera) when the mode changes:
    2 on entering follow (search the colour instead of faces), 1 on leaving it (faces again),
    None for nothing (other camera kinds, or no change)."""
    if not detect_on_camera or (old_mode == "follow") == (new_mode == "follow"):
        return None
    return 2 if new_mode == "follow" else 1


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


def color_controls(model):
    """The camera's /control settings for the colour to search (detect=2), sent before detect."""
    return [("color_h", model.h), ("color_s", model.s), ("color_v", model.v),
            ("color_htol", model.hue_tol), ("color_ltol", model.light_tol)]


def marker_from_raw(text):
    """/cameras/<camera>/marker_raw JSON -> Marker, or None (not seen, or unreadable)."""
    try:
        d = json.loads(text)
        return Marker(float(d["cx"]), float(d["cy"]), float(d["area"])) if d.get("seen") else None
    except (ValueError, KeyError, TypeError):
        return None
