# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The push rod that reaches the Pico board's DISPLAY button (SW1) through the front."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


@pytest.fixture(scope="module")
def ep():
    return echo_values("echo_pulsador")


def test_rod_clear_of_ghosts():
    assert is_empty("check_rod_vs_ghosts")


@pytest.mark.parametrize("press", [0, 1.3])
def test_rod_slides_freely_in_its_guide(press):
    assert is_empty("check_rod_vs_front", {"press": press})


def test_rod_does_not_touch_the_button_at_rest():
    assert is_empty("check_rod_on_button", {"press": 0})


def test_rod_presses_the_button_when_pushed():
    assert not is_empty("check_rod_on_button", {"press": 1.3})


def test_rod_cannot_fall_out_of_the_front(ep):
    assert ep["flange_d"] > ep["bore_d"] + 1


def test_rod_tip_stands_proud_of_the_front(ep):
    assert ep["tip_y"] <= -0.9


def test_guide_clear_of_the_oled_window():
    assert is_empty("check_guide_vs_window")


def test_rod_prints_standing_on_its_flange():
    lo, hi = stl_bbox(run_scad("pulsador"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] > 25
