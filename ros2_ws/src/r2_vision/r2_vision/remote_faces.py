# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Faces found on the camera itself (r2_domecam on an ESP32-S3): reading its lines and
turning its boxes the same way the camera node turns the picture (rotate, then flip)."""

import json
from urllib.parse import urlparse

FACES_PORT = 82


def faces_url(source):
    """http://cam:81/stream -> http://cam:82/faces (the same camera's faces)."""
    host = urlparse(source).hostname
    return f"http://{host}:{FACES_PORT}/faces" if host else None


def control_url(url, var, val):
    """http://cam:82/faces -> http://cam/control?var=rotate&val=90 (the camera's settings)."""
    host = urlparse(url).hostname
    return f"http://{host}/control?var={var}&val={val}" if host else None


def iter_lines(stream):
    """The lines of a chunked HTTP answer, each one as soon as it arrives. Looping over the
    response itself waits to fill an 8 KB buffer first: some 200 lines, seconds of lag."""
    buf = b""
    while True:
        data = stream.read1(4096)
        if not data:
            return
        buf += data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            yield line.decode("utf-8", "replace")


def parse_line(line):
    """One line from /faces -> dict(lat_ms, w, h, rot, mode, faces=[(x, y, w, h, score), ...],
    marker=(cx, cy, area) or None) or None.

    mode: "faces" or "color" (cameras that only find faces send no mode: "faces"). In colour mode
    marker is the blob the camera found, centre and area as fractions of the picture, or None.

    rot: the camera already turned the picture this much (clockwise) before searching it, so
    w, h and the boxes are those of the turned picture. Empty lines are the camera's keep-alive.
    """
    line = line.strip()
    if not line:
        return None
    try:
        d = json.loads(line)
        marker = d.get("marker")
        return {
            "mode": "color" if d.get("mode") == "color" else "faces",
            "marker": tuple(float(v) for v in marker[:3]) if marker else None,
            "lat_ms": float(d.get("lat_ms", 0)),
            "w": int(d["w"]),
            "h": int(d["h"]),
            "rot": int(d.get("rot", 0)) % 360,
            "faces": [tuple(float(v) for v in f[:5]) for f in d.get("faces", [])],
        }
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def orient_box(x, y, w, h, width, height, rotate=0, flip="none"):
    """A box in the sensor's picture -> the same box in the turned picture.

    rotate: 0/90/180/270 degrees clockwise, then flip: none/h/v/both, like the camera node.
    Returns (x, y, w, h, picture_width, picture_height).
    """
    if rotate == 90:
        x, y, w, h, width, height = height - (y + h), x, h, w, height, width
    elif rotate == 180:
        x, y = width - (x + w), height - (y + h)
    elif rotate == 270:
        x, y, w, h, width, height = y, width - (x + w), h, w, height, width
    if flip in ("h", "both"):
        x = width - (x + w)
    if flip in ("v", "both"):
        y = height - (y + h)
    return x, y, w, h, width, height


def orient_point(cx, cy, width, height, rotate=0, flip="none"):
    """A point (fractions of the sensor's picture) -> the same point in the turned picture,
    the same turning as orient_box."""
    x, y, _, _, ww, hh = orient_box(cx * width, cy * height, 0, 0, width, height, rotate, flip)
    return x / ww, y / hh


def marker_raw_json(d, rotate=0, flip="none"):
    """A colour-mode line (parse_line) -> the marker_raw JSON: the blob turned like the faces."""
    if d["marker"] is None:
        return json.dumps({"seen": False, "cx": 0.0, "cy": 0.0, "area": 0.0, "lat_ms": d["lat_ms"]})
    cx, cy, area = d["marker"]
    cx, cy = orient_point(cx, cy, d["w"], d["h"], rotate, flip)
    return json.dumps({"seen": True, "cx": cx, "cy": cy, "area": area, "lat_ms": d["lat_ms"]})
