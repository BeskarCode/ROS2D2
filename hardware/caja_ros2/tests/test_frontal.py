# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The front: carries the Pico board on 4 columns, shows the OLED through its window, has the
logo inlaid in black and blue, and prints face down."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


@pytest.fixture(scope="module")
def ef():
    return echo_values("echo_frontal")


def test_frontal_does_not_hit_ghosts():          # includes the Dupont plugs and their cables
    assert is_empty("check_frontal_vs_ghosts")


def test_oled_window_aligned():
    # the visible area sits inside the window's inner opening (the angles test checks the margins)
    v = echo_values("echo_oled_view")
    (x0, z0, x1, z1), (a0, b0, a1, b1) = v["win_inner"], v["active"]
    assert x0 < a0 and a1 < x1 and z0 < b0 and b1 < z1


def test_logo_inside_front_and_above_window(ef):
    lo, hi = stl_bbox(run_scad("logo_negro_montado"))
    assert lo[1] == pytest.approx(0, abs=0.01) and hi[1] == pytest.approx(0.6, abs=0.01)
    assert lo[2] > ef["oled_win_top"] + 3
    assert lo[0] > 0 and hi[0] < ef["W"]


def test_logos_do_not_overlap():
    assert is_empty("check_logo_overlap")


def test_columns_reach_the_pico_board(ef):
    assert is_empty("check_columns_short")             # columns shortened 0.2 mm do not touch the board
    assert not is_empty("check_columns_touch")         # columns lengthened 0.2 mm do


@pytest.mark.parametrize("p", ["frontal", "logo_negro", "logo_azul"])
def test_frontal_print_orientation_flat_face_down(p):
    lo, _ = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)


def test_logo_bodies_sit_in_the_front_face():
    # printed face down: the logo pieces sit at z 0..0.6 within the panel's footprint
    lo, hi = stl_bbox(run_scad("logo_azul"))
    assert hi[2] == pytest.approx(0.6, abs=0.01)


def test_monocolor_front_has_the_logo_engraved_1mm():
    assert is_empty("check_mono_logo_cavity")              # nothing inside the logo, 1 mm deep
    assert not is_empty("check_mono_logo_floor")           # but solid just behind it


def test_monocolor_front_prints_face_down():
    lo, _ = stl_bbox(run_scad("frontal_monocolor"))
    assert lo[2] == pytest.approx(0, abs=0.01)


def test_oled_window_viewing_angles():
    # review: a 26 x 15 window 24 mm in front of the display showed it whole only within +-5 deg
    import math
    v = echo_values("echo_oled_view")
    d = v["dist"]
    (x0, z0, x1, z1), (a0, b0, a1, b1) = v["win_inner"], v["active"]
    # left edge gives way to the DISPLAY push rod's guide (user OK'd ~12 deg on that side)
    assert math.degrees(math.atan((a0 - x0) / d)) >= 10 and math.degrees(math.atan((x1 - a1) / d)) >= 20
    assert math.degrees(math.atan((b0 - z0) / d)) >= 15 and math.degrees(math.atan((z1 - b1) / d)) >= 15


def test_oled_window_clear_of_the_columns():
    assert is_empty("check_window_vs_columns")


def test_pico_columns_have_room_for_the_insert():
    # review: 6.8 mm column round a 4 mm insert hole left ~1.1 mm of wall
    assert echo_values("echo_frontal")["col_d"] >= 8
