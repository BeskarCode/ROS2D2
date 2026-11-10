# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The boards and connectors, modelled as ghosts where they sit in the box, must fit inside the
walls and must not run into each other (that includes the room their plugs and cables need)."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


@pytest.fixture(scope="module")
def lay():
    return echo_values("echo_layout")


def test_ghosts_render_and_fit_inside_box(lay):
    W, D, H, wall = lay["W"], lay["D"], lay["H"], lay["wall"]
    lo, hi = stl_bbox(run_scad("ghosts"))
    assert lo[0] >= wall and lo[1] >= wall and lo[2] >= wall
    assert hi[0] <= W - wall and hi[2] <= H - wall
    assert hi[1] <= D - wall + 3.5          # only the Pi's ports go into the back wall


@pytest.mark.parametrize("a,b", [("pico", "pi"), ("pico", "conv"), ("pi", "conv"), ("conv", "xt60"),
                                 ("conv", "switch"), ("pi", "xt60"), ("pi", "switch"),
                                 ("xt60", "switch"), ("pico", "xt60"), ("pico", "switch")])
def test_ghosts_do_not_collide_with_each_other(a, b):
    assert is_empty("check_ghost_pair", {"ga": a, "gb": b}), (a, b)


def test_oled_view_center(lay):
    x0, ztop = lay["pico_x0"], lay["pico_ztop"]
    assert lay["oled_view_center"] == pytest.approx([x0 + 58.5, ztop - 71], abs=0.01)


def test_pi_ports_flush_with_the_back_outside(lay):
    # review: the jacks sat 2.5 mm behind the outer face, plugs could not seat
    assert lay["pi_port_face"] >= lay["D"] - 0.5


def test_cable_route_to_the_back_slot_is_kept_free():
    # the sensor cables (and the Pico's USB going out) run from the side channels to the back slot
    for g in ["pi", "conv", "xt60", "switch"]:
        assert is_empty("check_ghost_pair", {"ga": "cables", "gb": g}), g
