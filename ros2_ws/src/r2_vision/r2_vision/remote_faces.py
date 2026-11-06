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
    """One line from /faces -> dict(lat_ms, w, h, rot, faces=[(x, y, w, h, score), ...]) or None.

    rot: the camera already turned the picture this much (clockwise) before searching it, so
    w, h and the boxes are those of the turned picture. Empty lines are the camera's keep-alive.
    """
    line = line.strip()
    if not line:
        return None
    try:
        d = json.loads(line)
        return {
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
