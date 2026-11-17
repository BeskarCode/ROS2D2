# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""LED face without AMS: the same LED face with the logo and the names as deep pockets, and their fillings
printed apart (navy, blue, grey). The LED face with AMS must not change."""
import pathlib
import sys

import numpy as np
import pytest

from scad import is_empty, run_scad, stl_bbox, stl_volume

HERE = pathlib.Path(__file__).resolve().parents[1]
COLOURS = ["navy", "blue", "grey"]
sys.path.insert(0, str(HERE / "logo"))
import gen_na_grey as gg  # noqa: E402


# --- the LED face for AMS stays as it was (its STLs in stl/leds/) ----------------------------------
@pytest.mark.xfail(reason="stl/ and the guides are regenerated in Task 8", strict=False)
@pytest.mark.parametrize("part", ["wall_led", "wall_led_monocolor", "logo_navy_led", "logo_blue_led", "logo_grey_led"])
def test_led_face_unchanged(part):
    assert stl_volume(run_scad(part)) == pytest.approx(stl_volume(HERE / "stl" / "leds" / f"{part}.stl"), abs=0.01)


# --- the face: only the pockets differ ------------------------------------------------------------------
def test_same_face_behind_the_pockets():
    # inserts, columns, tabs, tubes, lens recesses, window, XT60...: identical from X 1.5 inwards
    assert is_empty("check_pared_no_ams_same_inside") and is_empty("check_wall_led_same_inside")


def test_pockets_deeper_and_closed_behind():
    lo, hi = stl_bbox(run_scad("na_pockets_montados"))
    assert lo[0] == pytest.approx(0, abs=0.01) and hi[0] == pytest.approx(1.4, abs=0.01)   # 1.1 mm of wall stays


@pytest.mark.parametrize("what", ["check_na_vs_holes", "check_na_vs_window", "check_na_vs_cuts"])
def test_pockets_clear_of_the_other_holes(what):
    assert is_empty(what)                             # 0.3 mm of wall at least round every pocket


def test_face_clear_of_ghosts():
    assert is_empty("check_pared_no_ams_vs_ghosts")


def test_face_prints_flat():
    lo, hi = stl_bbox(run_scad("wall_led_no_ams"))
    assert lo[2] == pytest.approx(0, abs=0.01)


# --- the fillings ----------------------------------------------------------------------------------------
def test_fillings_fit_with_play():
    assert is_empty("check_rellenos_vs_pared")        # 0.1 mm per side between filling and pocket


def test_fillings_flush():
    assert is_empty("check_rellenos_flush")


def test_fillings_fill_their_pockets():
    assert is_empty("check_rellenos_fill")            # nothing of a pocket left empty but the play


@pytest.mark.parametrize("c", COLOURS)
def test_fillings_apart(c):
    assert is_empty("check_rellenos_overlap", {"colour": c})


@pytest.mark.parametrize("c", COLOURS)
def test_filling_prints_flat(c):
    lo, hi = stl_bbox(run_scad(f"inlay_{c}"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(1.4, abs=0.01)    # 7 layers of 0.2


# --- the grey frame: thick enough to print alone, off the blue dots (logo/gen_na_grey.py) ----------------
def _runs_from_edge(a, axis, rev):
    """for each line across a side of the frame: how many grey pixels in a row from the outer edge."""
    b = a if axis == 0 else a.T
    b = b[::-1] if rev else b
    first = b.argmax(axis=0)                                       # the outer edge in each line
    out = []
    for j in range(b.shape[1]):
        k = first[j]
        n = 0
        while k + n < b.shape[0] and b[k + n, j]:
            n += 1
        out.append(n)
    return np.array(out)


def test_grey_frame_wide_enough():
    g = gg.load("logo_grey_na.svg")
    ys, xs = np.where(g)
    end = int(gg.px(2.5))                                          # the rounded corners left out
    sides = [_runs_from_edge(g[:, xs.min() + end:xs.max() - end], 0, False),   # top
             _runs_from_edge(g[:, xs.min() + end:xs.max() - end], 0, True),    # bottom
             _runs_from_edge(g[ys.min() + end:ys.max() - end, :xs.max() + 1], 1, False),   # left
             _runs_from_edge(g[ys.min() + end:ys.max() - end, :xs.max() + 1], 1, True)]    # right
    mm = [s * gg.PX * gg.MM_PER_UNIT for s in sides]
    assert min(m.min() for m in mm) >= gg.MIN_MM                   # 3 lines of a 0.4 nozzle (a little narrower under the dots)
    assert max(m.max() for m in mm) <= gg.FRAME_MM + 0.1


def test_grey_frame_clear_of_the_dots():                         # Review Focus 5
    assert not (gg.load("logo_grey_na.svg") & gg.dilate(gg.load("logo_blue.svg"), gg.px(0.15))).any()


def test_grey_frame_svg_up_to_date():
    assert (gg.frame(gg.load("logo_grey.svg"), gg.load("logo_blue.svg")) == gg.load("logo_grey_na.svg")).all()


def test_fillings_on_layers():
    import re
    d = float(re.search(r"^na_depth = ([\d.]+);", (HERE / "params.scad").read_text(), re.M).group(1))
    assert d == pytest.approx(1.4) and round(d / 0.2, 6) == int(round(d / 0.2))
