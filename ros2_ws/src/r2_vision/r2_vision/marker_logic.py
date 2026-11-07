# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The ROS-free decisions of the colour marker node (kept apart so they can be tested)."""

import json
import math

from r2_vision.color_marker import (bearing, color_warning, find_marker, match_fraction,
                                    model_from_pixel)


def wants_video(mode, preview):
    """The camera only sends video while someone needs it (it is on_demand)."""
    return mode == "follow" or bool(preview)


def detect_value(old_mode, new_mode, detect_on_camera):
    """What to tell the dome camera's own face finder when the mode changes: 0 on entering
    follow, 1 on leaving it, None for nothing (other camera kinds, or no change)."""
    if not detect_on_camera or (old_mode == "follow") == (new_mode == "follow"):
        return None
    return 0 if new_mode == "follow" else 1


def parse_pick(text):
    """/marker/pick JSON -> (x, y, hue_tol, light_tol) with x, y clamped to 0-1, or None."""
    try:
        d = json.loads(text)
        x, y = float(d["x"]), float(d["y"])
        hue_tol, light_tol = int(d["hue_tol"]), int(d["light_tol"])
    except (ValueError, KeyError, TypeError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0), hue_tol, light_tol


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
