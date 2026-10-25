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


def pixelate(img, x, y, w, h, blocks=8):
    """Blur a box into blocks x blocks flat squares, in place (to hide a face). Returns img."""
    H, W = img.shape[:2]
    x0, y0 = max(int(x), 0), max(int(y), 0)
    x1, y1 = min(int(x + w), W), min(int(y + h), H)
    if x1 <= x0 or y1 <= y0:
        return img
    xs = np.linspace(x0, x1, blocks + 1).astype(int)
    ys = np.linspace(y0, y1, blocks + 1).astype(int)
    for ya, yb in zip(ys[:-1], ys[1:]):
        for xa, xb in zip(xs[:-1], xs[1:]):
            if yb > ya and xb > xa:
                cell = img[ya:yb, xa:xb]
                cell[:] = cell.reshape(-1, cell.shape[-1]).mean(0).astype(img.dtype)
    return img
