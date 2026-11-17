# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Light pipes (rack box): the Pico's LEDs in box coordinates, the LED face (a dark tube from each hole
to its LED, logo moved down, names), today's face, and the translucent lenses flush with the face."""
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
    assert v["lp_tip_x"] == pytest.approx(31.0, abs=0.01)


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


# --- the LED face, today's face unchanged ------------------------------------------------------------
TODAY = {"wall": 39449.816, "wall_monocolor": 39299.452, "logo_navy": 81.994, "logo_blue": 121.116,
         "logo_grey": 22.435}                       # male XT60 (2026-11-14); the LED face must not change them


@pytest.mark.parametrize("part", list(TODAY))
def test_today_face_unchanged(part):
    assert stl_volume(run_scad(part)) == pytest.approx(TODAY[part], abs=0.01)


def test_led_holes_over_each_led():
    v = echo_values("echo_lp_holes")                # name -> [y, z, d]
    for name, (y, z) in SPEC.items():
        hy, hz, d = v[name]
        assert (hy, hz) == pytest.approx((y, z), abs=0.2) and d >= 3.2, name


def test_led_holes_go_through():
    assert is_empty("check_lp_holes_open")          # the LED face, inside each hole's core: nothing


def test_led_logo_in_its_band():
    lo, hi = stl_bbox(run_scad("logo_todo_led_montado"))
    assert lo[2] >= 16.5 and hi[2] <= 38.5          # XT60 / switch up to Z 16; the window's chamfer from Z 39
    assert hi[1] - lo[1] == pytest.approx(80, abs=0.5)


def test_led_face_clear_of_ghosts():
    assert is_empty("check_wall_led_vs_ghosts")


@pytest.mark.parametrize("what", ["check_labels_vs_holes", "check_labels_vs_logo_led", "check_labels_vs_window"])
def test_labels_clear(what):
    assert is_empty(what)


def test_labels_inside_the_face():
    lo, hi = stl_bbox(run_scad("lp_labels_montadas"))
    assert lo[1] >= 2 and hi[1] <= 93 and lo[2] >= 2 and hi[2] <= 143


@pytest.mark.parametrize("p", ["wall_led", "wall_led_monocolor", "logo_navy_led", "logo_blue_led", "logo_grey_led"])
def test_led_face_prints_flat(p):
    lo, hi = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)


# --- the tubes and the lenses -------------------------------------------------------------------------
def test_tubes_never_touch_the_board():
    assert is_empty("check_lp_tubes_vs_pcb")        # (the face against ghost_all(), LEDs too: test above)


def test_tube_bores_open_to_the_led():
    assert is_empty("check_lp_bores_open")


def test_tubes_end_just_over_the_leds():
    # the board rests on the columns' ends (X 32.45), the LED is up to 0.8 tall: 0.3..1.2 mm of air
    v = echo_values("echo_lp_tips")                 # name -> X of its tube's end; plus column end
    led_top = v["column_end"] - 0.8
    for name in SPEC:
        assert 0.3 <= led_top - v[name] <= 1.2, name


def test_lenses_fit_their_recesses():
    assert is_empty("check_lentes_vs_pared")        # disc in its recess, stem in its bore, with play


def test_lenses_flush_with_the_face():
    assert is_empty("check_lentes_flush")           # nothing stands out of the face


def test_lenses_print_flat():
    lo, hi = stl_bbox(run_scad("led_lenses"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(2.3, abs=0.05)
