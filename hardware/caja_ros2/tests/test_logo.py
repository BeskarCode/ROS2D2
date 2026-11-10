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
    # white, navy, blue, transparent, then the frame's grey (black at 65 % alpha) inside / outside the frame columns
    px = np.array([[[255, 255, 255, 255], [13, 34, 64, 255], [60, 110, 175, 255], [0, 0, 0, 0],
                    [0, 7, 13, 165], [0, 7, 13, 165]]], np.uint8)
    assert classify(px, frame_cols=5).tolist() == [[0, 1, 2, 0, 3, 0]]


@pytest.mark.parametrize("c", ["marino", "azul", "gris"])
def test_svgs_exist_with_logo_width(c):
    w, h = svg_size_mm(LOGO_DIR / f"logo_{c}.svg")
    assert w == pytest.approx(92, abs=0.2) and h == pytest.approx(15.4, abs=0.2)


@pytest.mark.skipif(not PNG.exists(), reason="the logo PNG lives in ROS2D2/docs (local only)")
@pytest.mark.parametrize("k", [1, 2, 3])
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
    ms = masks(px_mm=0.1)
    for m in ms:
        assert _pinches(m) == 0
    assert _pinches(ms[0] | ms[1] | ms[2]) == 0
    for i in range(3):
        for j in range(i + 1, 3):
            assert not (ms[i] & ms[j]).any()


def test_min_feature_detects_thin_line():
    m = np.zeros((40, 40), bool)
    m[10:30, 20:23] = True               # 0.3 mm wide at 0.1 mm/px
    assert min_feature_mm(m, px_mm=0.1) < 0.8


@pytest.mark.skipif(not PNG.exists(), reason="the logo PNG lives in ROS2D2/docs (local only)")
def test_no_thin_strokes_anywhere():
    # review: island thickness missed thin strokes attached to thick parts (0.3 mm blue leg stripe)
    from gen_logo import masks, thin_parts
    for m in masks(px_mm=0.1):
        assert thin_parts(m, px_mm=0.1, min_mm=0.8) <= 20     # largest thin cluster, px (0.2 mm^2)
