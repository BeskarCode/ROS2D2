# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The U shell: roof + both sides, slides down over base and front, vents mostly on top and sides."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


def test_shell_fits_assembled():
    assert is_empty("check_shell_assembled")      # shell ∩ (base ∪ front)


@pytest.mark.parametrize("dz", [20, 40, 60, 100])
def test_shell_slides_on_from_top(dz):
    assert is_empty("check_shell_slide", {"dz": dz})


def test_shell_clear_of_ghosts():
    assert is_empty("check_shell_vs_ghosts")


def test_top_tabs_meet_the_roof_screws():
    assert not is_empty("check_top_screws_hit_tabs")  # the roof's screw holes land on the tabs' inserts


def test_vent_area_top_and_sides():
    v = echo_values("echo_vents")
    assert v["top_mm2"] >= 1500 and v["left_mm2"] >= 800 and v["right_mm2"] >= 800


def test_overall_size():
    lo, hi = stl_bbox(run_scad("montaje_sin_orejetas"))
    size = [h - l for l, h in zip(lo, hi)]
    assert size == pytest.approx([107, 133, 125], abs=8)


def test_shell_prints_roof_down():
    lo, hi = stl_bbox(run_scad("carcasa"))
    assert lo[2] == pytest.approx(0, abs=0.01)
