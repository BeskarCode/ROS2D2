# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math

import numpy as np

from r2_vision.color_marker import (Marker, bearing, color_warning, find_marker,
                                    match_fraction, match_mask, model_from_pixel)

ORANGE = (0, 128, 255)


def canvas(w=200, h=100):
    return np.full((h, w, 3), 128, np.uint8)


def rect(img, x0, y0, x1, y1, bgr):
    img[y0:y1, x0:x1] = bgr


def test_pick_orange():
    img = canvas()
    rect(img, 50, 20, 110, 70, ORANGE)
    m = model_from_pixel(img, 80, 45, 10, 60)
    assert abs(m.h - 15) <= 1
    assert abs(match_fraction(img, m) - 60 * 50 / (200 * 100)) < 0.01


def test_red_wraps():
    import cv2
    m = model_from_pixel(np.full((10, 10, 3), (0, 0, 255), np.uint8), 5, 5, 10, 60)
    assert m.h == 0
    for hue in (178, 2):
        img = canvas()
        hsv = np.full((100, 200, 3), (hue, 255, 255), np.uint8)
        rect(img, 0, 0, 50, 50, cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0])
        assert match_mask(img, m)[10, 10] == 255
        assert match_mask(img, m)[80, 150] == 0


def test_find_marker_prefers_previous():
    img = canvas()
    rect(img, 10, 30, 40, 60, ORANGE)
    rect(img, 120, 10, 190, 90, ORANGE)
    m = model_from_pixel(img, 20, 40, 10, 60)
    left = find_marker(img, m, Marker(0.1, 0.5, 0.05))
    assert left.cx < 0.5
    assert find_marker(img, m, None).cx > 0.5


def test_find_marker_ignores_specks():
    img = canvas(200, 100)
    rect(img, 50, 20, 110, 70, ORANGE)
    m = model_from_pixel(img, 80, 45, 10, 60)
    img2 = canvas(200, 100)
    rect(img2, 10, 10, 15, 14, ORANGE)  # 20 px = 0.1 %
    assert find_marker(img2, m, None) is None


def test_bearing_sign():
    assert bearing(Marker(0.25, 0.5, 0.1), 60) > 0
    assert bearing(Marker(0.75, 0.5, 0.1), 60) < 0
    assert bearing(Marker(0.5, 0.5, 0.1), 60) == 0
    assert math.isclose(bearing(Marker(0.0, 0.5, 0.1), 60), math.radians(30))


def test_warnings():
    def px(bgr):
        return model_from_pixel(np.full((9, 9, 3), bgr, np.uint8), 4, 4, 10, 60)
    assert color_warning(px((0, 0, 0))) == "too dark"
    assert color_warning(px((128, 128, 128))) == "too pale"
    assert color_warning(px(ORANGE)) is None
