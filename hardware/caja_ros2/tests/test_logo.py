# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The ROS2D2 logo split into the black and the blue inlay, as SVG in mm, printable with a 0.4 nozzle."""
import pathlib
import re

import numpy as np
import pytest

from gen_logo import PNG, classify, load_png, min_feature_mm

LOGO_DIR = pathlib.Path(__file__).resolve().parent.parent / "logo"


def svg_size_mm(path):
    head = path.read_text(encoding="utf8")[:500]
    w = float(re.search(r'width="([\d.]+)mm"', head).group(1))
    h = float(re.search(r'height="([\d.]+)mm"', head).group(1))
    return w, h


def test_classify_colours():
    px = np.array([[[255, 255, 255, 255], [10, 10, 20, 255], [20, 60, 170, 255], [0, 0, 0, 0]]], np.uint8)
    assert classify(px).tolist() == [[0, 1, 2, 0]]


@pytest.mark.parametrize("c", ["negro", "azul"])
def test_svgs_exist_with_logo_width(c):
    w, h = svg_size_mm(LOGO_DIR / f"logo_{c}.svg")
    assert w == pytest.approx(80, abs=0.2) and h == pytest.approx(24.8, abs=0.5)


@pytest.mark.skipif(not PNG.exists(), reason="the logo PNG lives in ROS2D2/docs (local only)")
@pytest.mark.parametrize("k", [1, 2])
def test_no_feature_thinner_than_08mm(k):
    m = classify(load_png(px_mm=0.1))
    from gen_logo import clean
    assert min_feature_mm(clean(m == k, px_mm=0.1), px_mm=0.1) >= 0.8


def _pinches(m):
    a, b, c, d = m[:-1, :-1], m[:-1, 1:], m[1:, :-1], m[1:, 1:]
    return int(((a & d & ~b & ~c) | (b & c & ~a & ~d)).sum())


def test_fix_pinches_removes_corner_only_contacts():
    from gen_logo import fix_pinches
    m = np.zeros((4, 4), bool)
    m[1, 1] = m[2, 2] = True
    assert _pinches(m) == 1 and _pinches(fix_pinches(m)) == 0


@pytest.mark.skipif(not PNG.exists(), reason="the logo PNG lives in ROS2D2/docs (local only)")
def test_inlays_have_no_pinches_and_do_not_share_pixels():
    from gen_logo import masks
    neg, azu = masks(px_mm=0.1)
    assert _pinches(neg) == 0 and _pinches(azu) == 0 and _pinches(neg | azu) == 0
    assert not (neg & azu).any()


def test_min_feature_detects_thin_line():
    m = np.zeros((40, 40), bool)
    m[10:30, 20:23] = True               # 0.3 mm wide at 0.1 mm/px
    assert min_feature_mm(m, px_mm=0.1) < 0.8
