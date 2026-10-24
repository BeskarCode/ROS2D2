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
