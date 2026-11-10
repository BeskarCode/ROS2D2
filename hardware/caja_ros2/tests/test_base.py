# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The base: floor, back panel (Pi ports, XT60E-F, rocker switch, sensor cable slot), the Pi's
bracket, the converter's bosses and the ears that fix the box to the R2."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


def test_base_does_not_hit_ghosts():
    assert is_empty("check_base_vs_ghosts")


def test_pi_ports_pass_through_back():
    assert is_empty("check_ports_clear")          # the jacks pushed 10 mm out the back meet nothing


@pytest.mark.parametrize("what", ["xt60", "switch"])
def test_back_connectors_pass_through_back(what):
    assert is_empty("check_back_cut", {"ga": what})   # their body pushed through the wall meets nothing


def test_base_and_frontal_do_not_overlap():
    assert is_empty("check_base_vs_frontal")


def test_pi_standoffs_reach_the_pi():
    assert not is_empty("check_pi_standoffs_touch")    # standoffs lengthened 0.2 mm reach the board


def test_mount_ears_outside_footprint():
    W = echo_values("echo_layout")["W"]
    lo, hi = stl_bbox(run_scad("base_montada"))
    assert lo[0] < 0 and hi[0] > W                 # ears on both sides


def test_base_prints_flat():
    lo, _ = stl_bbox(run_scad("base"))
    assert lo[2] == pytest.approx(0, abs=0.01)


def test_back_top_tab_is_supported_for_printing():
    assert is_empty("check_back_tab_supported")      # nothing hangs in the air under it


def test_converter_inserts_leave_floor_under_them():
    assert is_empty("check_conv_insert_floor")       # >= 1.5 mm of floor below each insert hole


def test_right_low_vents_not_blocked_by_the_pi_bracket():
    assert is_empty("check_right_vents_open")


def test_switch_cut_is_the_panel_hole_not_the_bezel():
    assert echo_values("echo_back")["sw_cut"] == [19.2, 13]


def test_xt60_screw_holes_apart_from_body_cut():
    v = echo_values("echo_back")
    gap = v["xt60_hole_pitch"] / 2 - v["xt60_body"][1] / 2 - v["m3_clear"] / 2
    assert gap >= 1.5
