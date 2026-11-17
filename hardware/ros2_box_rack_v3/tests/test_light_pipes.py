# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Light pipes (rack box): the Pico's LEDs in box coordinates, the LED face (a dark tube from each hole
to its LED, logo moved down, names), today's face, and the translucent lenses flush with the face."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox, stl_volume

# each LED on the Pico board (bx, by), from r2_pico_carrier.kicad_pcb: on the main face at (90 - bx, ztop - by)
BOARD = {"VL1": (72.6, 12), "VL2": (72.6, 24), "VL3": (72.6, 39), "VL4": (72.6, 51),
         "US1": (21, 12), "US2": (21, 22), "US3": (21, 32), "US4": (21, 42), "US5": (21, 52), "PWR": (40.8, 59.5),
         "PICO": (34.5, 6.8)}
BASE = {"PICO": 12.0}       # the Pico's own LED, on the Pico (on its sockets): 12 mm over the board's face
SPEC = BOARD
TUBES = [n for n in BOARD if n not in BASE]     # the Pico LED is close to the face: lens + bore, no tube


# --- the LEDs and the light test rod -------------------------------------------------------------
def test_leds_where_the_spec_says():
    v = echo_values("echo_leds")
    for name, (bx, by) in BOARD.items():
        x, wy, wz = v[name]
        assert (wy, wz) == pytest.approx((90 - bx, v["pico_ztop"] - by), abs=0.05)
        assert x == pytest.approx(v["pico_x"] - BASE.get(name, 0), abs=0.01), name
    assert v["lp_tip_x"] == pytest.approx(v["pico_x"] - 1.5, abs=0.01)     # LED 0.8 + air 0.7


# --- ghosts around the LEDs ------------------------------------------------------------------------
def test_led_ghosts_sit_on_the_board_under_each_led():
    lo, hi = stl_bbox(run_scad("ghost_leds_only"))
    assert lo[0] == pytest.approx(2.5 + 1, abs=0.01)          # the QWIIC cable reaches wall + 1
    assert hi[0] == pytest.approx(2.5 + 14, abs=0.01)         # all of it stands on the parts face


@pytest.mark.parametrize("name", list(SPEC))
def test_each_led_ghost_is_where_its_led_is(name):
    assert not is_empty("check_led_ghost_at", {"led": name})


def test_vl_dupont_ghost_leaves_the_vl_leds_free():
    assert is_empty("check_vl_dupont_vs_vl_leds")


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
    for name in TUBES:
        assert 0.3 <= led_top - v[name] <= 1.2, name
    assert "PICO" not in v                          # no tube for the Pico LED


def test_eleven_leds_ten_tubes():
    v = echo_values("echo_layout")
    assert v["n_leds"] == 11 and v["n_tubes"] == 10 and v["lp_lens_n"] == 13     # 11 lenses + 2 spares


def test_pico_led_seen_through_the_wall():
    v = echo_values("echo_lp_tips")
    assert v["pico_led_top"] - v["wall"] >= 0.3     # air between the face's inside and the LED
    assert v["stem_end"] <= v["wall"]               # the lens stem stays in the wall's bore


def test_lens_recess_has_its_chamfer():
    assert is_empty("check_lens_chamfer")           # a ring 0.4 wide at each mouth: no wall left in it


def test_lens_fits_have_play():
    v = echo_values("echo_layout")
    assert (v["lp_bore"] - v["lp_stem_d"]) / 2 >= 0.15 - 1e-9
    assert (v["lp_hole"] - v["lp_lens_d"]) / 2 >= 0.25 - 1e-9


def test_pico_lens_clear_of_the_other_cuts():
    assert is_empty("check_pico_lens_vs_cuts")      # 1 mm of face round it: OLED window, USB recess, rod, bays, logo pockets


def test_lenses_fit_their_recesses():
    assert is_empty("check_lentes_vs_pared")        # disc in its recess, stem in its bore, with play


def test_lenses_flush_with_the_face():
    assert is_empty("check_lentes_flush")           # nothing stands out of the face


def test_lenses_print_flat():
    lo, hi = stl_bbox(run_scad("led_lenses"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[2] == pytest.approx(2.3, abs=0.05)
