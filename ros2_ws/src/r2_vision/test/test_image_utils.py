# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from types import SimpleNamespace

import numpy as np

from r2_vision.image_utils import biggest, image_to_bgr, pixelate


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


def test_pixelate_turns_the_box_into_flat_blocks():
    img = np.random.randint(0, 255, (40, 40, 3), np.uint8)
    out = pixelate(img.copy(), 10, 10, 20, 20, blocks=2)
    block = out[10:20, 10:20].reshape(-1, 3)
    assert (block == block[0]).all()                                  # one colour per block
    assert np.array_equal(block[0], img[10:20, 10:20].reshape(-1, 3).mean(0).astype(np.uint8))


def test_pixelate_leaves_the_rest_alone():
    img = np.random.randint(0, 255, (40, 40, 3), np.uint8)
    out = pixelate(img.copy(), 10, 10, 20, 20)
    assert np.array_equal(out[:10], img[:10])
    assert np.array_equal(out[:, 30:], img[:, 30:])


def test_pixelate_clips_boxes_off_the_picture():
    img = np.random.randint(0, 255, (40, 40, 3), np.uint8)
    pixelate(img, -15, 30, 30, 30)       # partly outside: no error
    pixelate(img, 50, 50, 10, 10)        # fully outside: no error
