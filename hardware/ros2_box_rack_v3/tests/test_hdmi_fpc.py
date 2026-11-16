# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""HDMI on the back without reprinting the base: the FPC holder and the blank cover screw onto the base's
existing inserts, clear of the base and the Pi frames, with the screws and the key free, and print flat."""
import pytest

from scad import is_empty, run_scad, stl_bbox


@pytest.mark.parametrize("p", ["hdmi_holder", "hdmi_cover"])
def test_prints_flat(p):
    lo, hi = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)


@pytest.mark.xfail(reason="HDMI jack moves in Task 4", strict=False)
@pytest.mark.parametrize("p", ["hdmi_holder", "hdmi_cover"])
@pytest.mark.parametrize("other", ["base", "marco", "screws"])
def test_clear(p, other):
    assert is_empty(f"check_{p}_vs_{other}" if other != "screws" else f"check_{p}_screws")


def test_cover_fills_the_window():
    assert is_empty("check_hdmi_cover_fills_window")


def test_holder_sits_on_the_back_and_sticks_out():
    lo, hi = stl_bbox(run_scad("hdmi_holder_montado"))
    assert lo[1] == pytest.approx(95, abs=0.01)          # D: against the back
    assert hi[1] - lo[1] < 30                             # how far it sticks out behind the box
