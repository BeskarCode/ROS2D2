"""sensor_msgs/Image <-> numpy without cv_bridge (keeps us free of its numpy/OpenCV version ties)."""

import numpy as np

CHANNELS = {"bgr8": 3, "rgb8": 3, "mono8": 1}


def image_to_bgr(msg):
    """Return the picture as a BGR (or grey, for mono8) numpy array, or None if unsupported."""
    ch = CHANNELS.get(msg.encoding)
    if ch is None:
        return None
    buf = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    img = buf[:, :msg.width * ch]
    img = img.reshape(msg.height, msg.width, ch) if ch > 1 else img
    if msg.encoding == "rgb8":
        img = img[:, :, ::-1]
    return np.ascontiguousarray(img)


def biggest(boxes):
    """Index of the biggest box (x, y, w, h, ...): the closest person. None if empty."""
    if boxes is None or len(boxes) == 0:
        return None
    return int(np.argmax(boxes[:, 2] * boxes[:, 3]))
