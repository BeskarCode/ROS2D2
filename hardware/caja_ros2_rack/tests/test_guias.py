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


# --- the LED face, today's face unchanged ------------------------------------------------------------
TODAY = {"pared": 39695.404, "pared_monocolor": 39545.04, "logo_marino": 81.994, "logo_azul": 121.116,
         "logo_gris": 22.435}                       # measured before the LED face existed


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
    assert is_empty("check_pared_led_vs_ghosts")


@pytest.mark.parametrize("what", ["check_labels_vs_holes", "check_labels_vs_logo_led", "check_labels_vs_window"])
def test_labels_clear(what):
    assert is_empty(what)


def test_labels_inside_the_face():
    lo, hi = stl_bbox(run_scad("lp_labels_montadas"))
    assert lo[1] >= 2 and hi[1] <= 93 and lo[2] >= 2 and hi[2] <= 143


@pytest.mark.parametrize("p", ["pared_led", "pared_led_monocolor", "logo_marino_led", "logo_azul_led", "logo_gris_led"])
def test_led_face_prints_flat(p):
    lo, hi = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)


# --- the translucent piece and its hooks -------------------------------------------------------------
def test_piece_clear_of_the_face():
    assert is_empty("check_guias_vs_pared")         # assembled: neither rods nor frame touch the LED face


@pytest.mark.parametrize("what", ["check_guias_vs_ghosts", "check_guias_vs_pcb"])
def test_piece_never_touches_the_board(what):
    assert is_empty(what)                           # ghost_all() has the LEDs, D2, J3, Dupont, cables


def test_tips_leave_air_over_the_leds():
    v = echo_values("echo_lp_tips")                 # name -> X of its rod's tip; LED top at 32.5 - 0.8
    for name in SPEC:
        assert 0.3 <= (32.5 - 0.8) - v[name] <= 0.8, name


def test_piece_is_held():
    assert not is_empty("check_guias_held")         # pushed 0.5 inwards, the hooks stop it


def test_piece_rests_on_the_wall_only():
    assert not is_empty("check_guias_stops_at_the_wall")   # pushed 0.1 outwards, it meets the wall


def test_hooks_clear_of_ghosts():
    assert is_empty("check_hooks_vs_ghosts")        # without the piece, the hooks are in nobody's way


def test_piece_prints_standing():
    lo, hi = stl_bbox(run_scad("guias_luz"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(31.2, abs=0.1)
