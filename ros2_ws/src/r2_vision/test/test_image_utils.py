from types import SimpleNamespace

import numpy as np

from r2_vision.image_utils import biggest, image_to_bgr


def make_msg(img, encoding, pad=0):
    h, w = img.shape[:2]
    ch = 1 if img.ndim == 2 else img.shape[2]
    rows = img.reshape(h, w * ch)
    if pad:
        rows = np.hstack([rows, np.zeros((h, pad), np.uint8)])
    return SimpleNamespace(height=h, width=w, step=w * ch + pad,
                           encoding=encoding, data=rows.tobytes())


def test_bgr_roundtrip():
    img = np.random.randint(0, 255, (4, 6, 3), np.uint8)
    assert np.array_equal(image_to_bgr(make_msg(img, "bgr8")), img)


def test_rgb_is_swapped():
    img = np.random.randint(0, 255, (4, 6, 3), np.uint8)
    assert np.array_equal(image_to_bgr(make_msg(img, "rgb8")), img[:, :, ::-1])


def test_row_padding_is_dropped():
    img = np.random.randint(0, 255, (3, 5, 3), np.uint8)
    assert np.array_equal(image_to_bgr(make_msg(img, "bgr8", pad=7)), img)


def test_mono():
    img = np.random.randint(0, 255, (3, 5), np.uint8)
    assert np.array_equal(image_to_bgr(make_msg(img, "mono8")), img)


def test_unsupported_encoding():
    img = np.zeros((2, 2, 3), np.uint8)
    assert image_to_bgr(make_msg(img, "yuv422")) is None


def test_biggest():
    boxes = np.array([[0, 0, 10, 10], [5, 5, 30, 20], [1, 1, 20, 20]], np.float32)
    assert biggest(boxes) == 1
    assert biggest(None) is None
    assert biggest(np.zeros((0, 15))) is None
