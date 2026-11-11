# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Option C (rack blade): ghosts fit and do not collide, every printed part stays clear of them,
the parts fit together, the screws go through holes into inserts, everything prints flat."""
import math

import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox


@pytest.fixture(scope="module")
def lay():
    return echo_values("echo_layout")


# --- ghosts -------------------------------------------------------------------------------------
def test_ghosts_fit_inside(lay):
    W, D, H, wall = lay["W"], lay["D"], lay["H"], lay["wall"]
    lo, hi = stl_bbox(run_scad("ghosts"))
    assert lo[0] >= wall - 0.01 and lo[1] >= wall - 0.01 and lo[2] >= wall - 0.01
    assert hi[0] <= W - wall + 0.01 and hi[2] <= H - wall + 0.01
    assert hi[1] <= D + 0.01                      # only the Pi's jacks reach the outside of the back


@pytest.mark.parametrize("a,b", [("pico", "pi"), ("pico", "conv"), ("pi", "conv"), ("pico", "xt60"),
                                 ("pico", "switch"), ("xt60", "switch"), ("conv", "xt60"), ("pi", "xt60"),
                                 ("cables", "pi"), ("cables", "conv"), ("cables", "xt60"), ("cables", "switch"),
                                 ("hdmi", "pico"), ("hdmi", "switch"), ("hdmi", "xt60"), ("hdmi", "cables")])
def test_ghost_pairs_do_not_collide(a, b):
    assert is_empty("check_ghost_pair", {"ga": a, "gb": b}), (a, b)


def test_pi_ports_flush_with_the_back(lay):
    assert lay["pi_port_face"] >= lay["D"] - 0.5


# --- main face ----------------------------------------------------------------------------------
def test_main_wall_clear_of_ghosts():
    assert is_empty("check_pared_vs_ghosts")


def test_oled_window_viewing_angles():
    v = echo_values("echo_oled_view")
    d = v["dist"]
    (y0, z0, y1, z1), (a0, b0, a1, b1) = v["win_inner"], v["active"]
    ang = lambda m: math.degrees(math.atan(m / d))
    assert min(ang(a0 - y0), ang(y1 - a1)) >= 10 and max(ang(a0 - y0), ang(y1 - a1)) >= 20
    assert ang(b0 - z0) >= 15 and ang(z1 - b1) >= 15


@pytest.mark.parametrize("what", ["check_window_vs_columns", "check_guide_vs_window"])
def test_window_clear(what):
    assert is_empty(what)


def test_columns_reach_the_board():
    assert is_empty("check_columns_short") and not is_empty("check_columns_touch")


def test_logo_inside_the_main_face(lay):
    lo, hi = stl_bbox(run_scad("logo_todo_montado"))          # all 3 colours: the ends are blue and grey
    assert lo[0] == pytest.approx(0, abs=0.01) and hi[0] == pytest.approx(0.6, abs=0.01)
    assert lo[1] > 0 and hi[1] < lay["D"]
    assert hi[1] - lo[1] == pytest.approx(80, abs=0.5)


def test_logos_do_not_overlap():
    assert is_empty("check_logo_overlap")


def test_logo_reads_from_outside():
    # the grey frame of the dot panel is the logo's left end; seen from outside (from -X), +Y is on
    # the left, so the grey body must sit at larger Y than the navy "ROS"
    g = stl_bbox(run_scad("logo_gris_montado"))
    n = stl_bbox(run_scad("logo_marino_montado"))
    assert (g[0][1] + g[1][1]) / 2 > (n[0][1] + n[1][1]) / 2


@pytest.mark.parametrize("p", ["pared", "logo_marino", "logo_azul", "logo_gris", "pared_monocolor", "pulsador",
                               "base", "tapa", "marco_pi4", "marco_pi5"])
def test_prints_flat(p):
    lo, hi = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)
    assert all(h - l <= 250 for l, h in zip(lo, hi))


# --- push rod -------------------------------------------------------------------------------------
def test_rod_clear_of_ghosts():
    assert is_empty("check_rod_vs_ghosts")


@pytest.mark.parametrize("press", [0, 1.3])
def test_rod_slides_in_its_guide(press):
    assert is_empty("check_rod_vs_pared", {"press": press})


def test_rod_presses_the_button_only_when_pushed():
    assert is_empty("check_rod_on_button", {"press": 0})
    assert not is_empty("check_rod_on_button", {"press": 1.3})


# --- base -------------------------------------------------------------------------------------------
def test_base_clear_of_ghosts():
    assert is_empty("check_base_vs_ghosts")


def test_pi_ports_pass_through_the_back():
    assert is_empty("check_ports_clear")


def test_pi_low_converter_high_with_a_gap():
    v = echo_values("echo_layout")
    assert v["conv_z0"] - v["pi_top"] >= 4.5                  # the converter's heat goes up, away from the Pi
    assert v["pi_z0"] - v["wall"] >= 14.5                     # room for the angled USB-C / micro-HDMI plugs


def test_hdmi_jack_passes_through_the_back():
    assert is_empty("check_hdmi_cut")


def test_xt60_bosses_clear_of_its_body():
    assert is_empty("check_xt60_bosses")


# --- back frame (Pi 4 / Pi 5) --------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["pi4", "pi5"])
def test_frame_lets_the_jacks_through(model):
    assert is_empty("check_marco_ports", {"model": model})


@pytest.mark.parametrize("model", ["pi4", "pi5"])
def test_frame_clear_of_the_base_and_the_ghosts(model):
    assert is_empty("check_marco_vs_base", {"model": model})
    assert is_empty("check_marco_vs_ghosts", {"model": model})


@pytest.mark.parametrize("model", ["pi4", "pi5"])
def test_frame_fills_the_window(model):
    assert is_empty("check_marco_fills_window", {"model": model})


def test_xt60_passes_through_the_main_face():
    assert is_empty("check_xt60_cut")


def test_switch_passes_through_the_main_face():
    assert is_empty("check_switch_cut")


def test_pi_standoffs_reach_the_pi():
    assert not is_empty("check_pi_standoffs_touch")


def test_base_and_main_wall_do_not_overlap():
    assert is_empty("check_base_vs_pared")


def test_mount_ears_stick_out(lay):
    lo, hi = stl_bbox(run_scad("base"))
    assert lo[1] < 0 and hi[1] > lay["D"]


# --- shell ------------------------------------------------------------------------------------------
def test_shell_fits_assembled():
    assert is_empty("check_tapa_assembled")


@pytest.mark.parametrize("dz", [20, 60, 130])
def test_shell_slides_on_from_above(dz):
    assert is_empty("check_tapa_slide", {"dz": dz})


def test_shell_clear_of_ghosts():
    assert is_empty("check_tapa_vs_ghosts")


def test_vents():
    v = echo_values("echo_vents")
    assert v["top_mm2"] >= 1000 and v["right_mm2"] >= 800 and v["front_mm2"] >= 300


def test_overall_size_and_volume():
    lo, hi = stl_bbox(run_scad("montaje_sin_orejetas"))
    size = [h - l for l, h in zip(lo, hi)]
    assert size == pytest.approx([78, 95, 145], abs=3)
    assert size[0] * size[1] * size[2] / 1e6 < 1.1          # litres: well under the first box's 1.78


# --- hardware ---------------------------------------------------------------------------------------
EXPECTED = {"ins_m3": 19, "ins_m25": 4, "m3x8_flat": 9, "m3x6_pan": 8, "m3x6_cyl": 2, "m3x10_flat": 0, "nut_m3": 0,
            "m25x6": 4, "m4x12": 4}


def test_bom_counts():
    v = echo_values("echo_bom")
    assert {k: v[k] for k in EXPECTED} == EXPECTED and v["inserts_without_screw"] == 0


@pytest.mark.parametrize("model", ["pi4", "pi5"])
@pytest.mark.parametrize("kind", ["ins_m3", "ins_m25", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m25x6"])
def test_hardware_only_goes_through_holes(kind, model):
    assert is_empty("check_screws_vs_parts", {"kind": kind, "model": model})
