# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Light pipes (rack box): the Pico's LEDs in box coordinates, the light test rod, the LED face
(holes, logo moved down, names) with today's face unchanged, and the optional translucent piece."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox, stl_volume

# where each LED shows on the main face (Y, Z), from the spec
SPEC = {"VL1": (17.4, 112.5), "VL2": (17.4, 100.5), "VL3": (17.4, 85.5), "VL4": (17.4, 73.5),
        "US1": (69, 112.5), "US2": (69, 102.5), "US3": (69, 92.5), "US4": (69, 82.5), "US5": (69, 72.5),
        "PWR": (49.2, 65)}


# --- the LEDs and the light test rod -------------------------------------------------------------
def test_leds_where_the_spec_says():
    v = echo_values("echo_leds")
    for name, (y, z) in SPEC.items():
        x, wy, wz = v[name]
        assert (wy, wz) == pytest.approx((y, z), abs=0.05) and x == pytest.approx(32.5, abs=0.01)
    assert v["lp_tip_x"] == pytest.approx(31.2, abs=0.01)


def test_light_test_rod_prints_standing():
    lo, hi = stl_bbox(run_scad("prueba_luz"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(31.2, abs=0.05)


# --- ghosts around the LEDs ------------------------------------------------------------------------
def test_led_ghosts_sit_on_the_board_under_each_led():
    lo, hi = stl_bbox(run_scad("ghost_leds_only"))
    assert lo[0] == pytest.approx(2.5 + 1, abs=0.01)          # the QWIIC cable reaches wall + 1
    assert hi[0] == pytest.approx(32.5, abs=0.01)             # all of it stands on the parts face


@pytest.mark.parametrize("name", list(SPEC))
def test_each_led_ghost_is_where_its_led_is(name):
    assert not is_empty("check_led_ghost_at", {"led": name})


def test_vl_dupont_ghost_leaves_the_vl_leds_free():
    assert is_empty("check_vl_dupont_vs_vl_leds")
