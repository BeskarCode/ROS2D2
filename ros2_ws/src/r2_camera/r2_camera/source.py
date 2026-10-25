"""Opening a camera source with OpenCV: USB webcam or network stream."""

import os
import sys

import cv2


def parse_source(source):
    """'0' -> 0 (device index); anything else (/dev/..., URL) stays a string."""
    source = str(source).strip()
    return int(source) if source.isdigit() else source


def is_network(source):
    return isinstance(source, str) and "://" in source


def is_file(source):
    """A video file (for testing without a camera), not a device or a URL."""
    return (isinstance(source, str) and not source.startswith("/dev/")
            and not is_network(source) and os.path.isfile(source))


def open_capture(source, width, height, fps, fourcc):
    """Open a camera and ask for the given format. Returns None if it can't be opened."""
    if is_network(source) or is_file(source):
        # ESP32 / IP cameras and video files: size and fps are decided by the source itself
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    else:
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
        cap = cv2.VideoCapture(source, backend)
        if cap.isOpened():
            if fourcc:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc[:4].ljust(4)))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     # always the newest picture
    return cap


def parse_v4l2_formats(text):
    """`v4l2-ctl --list-formats-ext` output -> {fourcc: [(width, height, best_fps), ...]}.

    Sizes keep the driver's order without repeats; best_fps is the highest the camera
    offers at that size.
    """
    modes, fourcc, size = {}, None, None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and "'" in line:
            fourcc = line.split("'")[1]
            modes.setdefault(fourcc, {})
        elif line.startswith("Size:") and fourcc:
            w, h = line.split()[-1].split("x")
            size = (int(w), int(h))
            modes[fourcc].setdefault(size, 0.0)
        elif line.startswith("Interval:") and fourcc and size and "(" in line:
            fps = float(line.split("(")[1].split()[0])
            modes[fourcc][size] = max(modes[fourcc][size], fps)
    return {f: [(w, h, fps) for (w, h), fps in sizes.items()] for f, sizes in modes.items()}


def list_modes(device, fourcc):
    """'640x480@30' strings a V4L2 camera offers in that pixel format ([] if unknown)."""
    import subprocess
    try:
        out = subprocess.run(["v4l2-ctl", "-d", str(device), "--list-formats-ext"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    modes = parse_v4l2_formats(out).get(fourcc) or next(iter(parse_v4l2_formats(out).values()), [])
    return [f"{w}x{h}@{fps:g}" for w, h, fps in modes]
