# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""LED face without AMS: the same LED face with the logo and the names as deep pockets, and their fillings
printed apart (navy, blue, grey). The LED face with AMS must not change."""
import pathlib

import pytest

from scad import is_empty, run_scad, stl_bbox, stl_volume

HERE = pathlib.Path(__file__).resolve().parents[1]
COLOURS = ["navy", "blue", "grey"]


# --- the LED face for AMS stays as it was (its STLs in stl/leds/) ----------------------------------
@pytest.mark.parametrize("part", ["wall_led", "wall_led_monocolor", "logo_navy_led", "logo_blue_led", "logo_grey_led"])
def test_led_face_unchanged(part):
    assert stl_volume(run_scad(part)) == pytest.approx(stl_volume(HERE / "stl" / "leds" / f"{part}.stl"), abs=0.01)


# --- the face: only the pockets differ ------------------------------------------------------------------
def test_same_face_behind_the_pockets():
    # inserts, columns, tabs, tubes, lens recesses, window, XT60...: identical from X 1.5 inwards
    assert is_empty("check_pared_no_ams_same_inside") and is_empty("check_wall_led_same_inside")


def test_pockets_deeper_and_closed_behind():
    lo, hi = stl_bbox(run_scad("na_pockets_montados"))
    assert lo[0] == pytest.approx(0, abs=0.01) and hi[0] == pytest.approx(1.5, abs=0.01)   # 1 mm of wall stays


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
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(1.5, abs=0.01)
