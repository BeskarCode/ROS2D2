# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Pick a colour from a picture, find the biggest blob of it, and turn its position into a bearing."""

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ColorModel:
    h: int          # OpenCV hue, 0-179
    s: int          # 0-255
    v: int          # 0-255
    hue_tol: int
    light_tol: int  # tolerance on both s and v


@dataclass
class Marker:
    cx: float       # image fractions, 0-1
    cy: float
    area: float


def model_from_pixel(bgr, x, y, hue_tol, light_tol, patch=7):
    """Median HSV of the patch x patch square around (x, y), clipped to the picture."""
    hh, ww = bgr.shape[:2]
    r = patch // 2
    x0, x1 = max(0, int(x) - r), min(ww, int(x) + r + 1)
    y0, y1 = max(0, int(y) - r), min(hh, int(y) + r + 1)
    hsv = cv2.cvtColor(np.ascontiguousarray(bgr[y0:y1, x0:x1]), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    h, s, v = (int(c) for c in np.median(hsv, axis=0))
    return ColorModel(h, s, v, int(hue_tol), int(light_tol))


def color_warning(m):
    if m.v < 50:
        return "too dark"
    if m.s < 60:
        return "too pale"
    return None


def match_mask(bgr, m):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s_lo, s_hi = max(0, m.s - m.light_tol), min(255, m.s + m.light_tol)
    v_lo, v_hi = max(0, m.v - m.light_tol), min(255, m.v + m.light_tol)
    h_lo, h_hi = m.h - m.hue_tol, m.h + m.hue_tol
    if h_lo >= 0 and h_hi <= 179:
        return cv2.inRange(hsv, (h_lo, s_lo, v_lo), (h_hi, s_hi, v_hi))
    # Hue wraps around 0/179 (red): two ranges
    if h_lo < 0:
        ranges = [(0, h_hi), (180 + h_lo, 179)]
    else:
        ranges = [(h_lo, 179), (0, h_hi - 180)]
    mask = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in ranges:
        mask |= cv2.inRange(hsv, (max(0, lo), s_lo, v_lo), (min(179, hi), s_hi, v_hi))
    return mask


def match_fraction(bgr, m):
    return float(np.count_nonzero(match_mask(bgr, m))) / (bgr.shape[0] * bgr.shape[1])


def find_marker(bgr, m, prev, min_area=0.004):
    """Biggest blob (or, with prev, the one nearest to it) of at least min_area of the picture."""
    hh, ww = bgr.shape[:2]
    n, _, stats, cents = cv2.connectedComponentsWithStats(match_mask(bgr, m), connectivity=8)
    best, best_key = None, None
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA] / (hh * ww)
        if area < min_area:
            continue
        cand = Marker(float(cents[i][0]) / ww, float(cents[i][1]) / hh, float(area))
        key = (math.hypot(cand.cx - prev.cx, cand.cy - prev.cy) if prev else -area)
        if best_key is None or key < best_key:
            best, best_key = cand, key
    return best


def bearing(marker, hfov_deg):
    """Radians, REP 103 (positive to the left)."""
    return (0.5 - marker.cx) * math.radians(hfov_deg)
