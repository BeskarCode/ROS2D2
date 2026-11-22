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
    # the straight USB plug sits in the face's 1 mm recess (usb_recess)
    assert lo[0] >= wall - 1.0 - 0.01 and lo[1] >= wall - 0.01 and lo[2] >= wall - 0.01
    assert hi[0] <= W - wall + 0.01 and hi[2] <= H - wall + 0.01
    assert hi[1] <= D + 0.01                      # only the Pi's jacks reach the outside of the back


@pytest.mark.parametrize("a,b", [("pico", "pi"), ("pico", "conv"), ("pi", "conv"), ("pico", "xt60"),
                                 ("pico", "switch"), ("xt60", "switch"), ("conv", "xt60"), ("pi", "xt60"),
                                 ("cables", "pi"), ("cables", "conv"), ("cables", "xt60"), ("cables", "switch"),
                                 ("hdmi", "pico"), ("hdmi", "switch"), ("hdmi", "xt60"), ("hdmi", "cables"),
                                 ("leds", "cables"), ("leds", "xt60"), ("leds", "switch"), ("leds", "conv"),
                                 ("usb", "pico"), ("usb", "conv"), ("usb", "leds"), ("usb", "pi")])
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
    g = stl_bbox(run_scad("logo_grey_montado"))
    n = stl_bbox(run_scad("logo_navy_montado"))
    assert (g[0][1] + g[1][1]) / 2 > (n[0][1] + n[1][1]) / 2


@pytest.mark.parametrize("p", ["wall", "logo_navy", "logo_blue", "logo_grey", "wall_monocolor", "push_rod",
                               "base", "shell", "frame_pi4", "frame_pi5"])
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


def test_xt60_flange_sits_flat_inside():
    assert is_empty("check_xt60_flange_seat")       # nothing behind the wall where its flange and body go


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


def test_xt60_passes_through_the_front():
    assert is_empty("check_xt60_cut")


def test_switch_passes_through_the_front():
    assert is_empty("check_switch_cut")


def test_front_clear_of_ghosts():
    assert is_empty("check_front_vs_ghosts")


@pytest.mark.parametrize("dz", [1, 40, 150])
def test_shell_lifts_off_without_the_front(dz):
    # the shell (roof + right side) goes straight up: the fixed front, the XT60 and the switch stay
    assert is_empty("check_shell_lift", {"dz": dz})


def test_power_on_the_front_above_the_pi(lay):
    # XT60 and switch on the narrow front (y = 0), Pi side, over the Pi; the converter far enough behind
    assert lay["xt60_x"] > lay["div_x1"] and lay["sw_x"] > lay["div_x1"]
    assert lay["xt60_z0"] >= lay["pi_top"] and lay["conv_y"] >= 27.5


def test_pi_standoffs_reach_the_pi():
    assert not is_empty("check_pi_standoffs_touch")


def test_base_and_main_wall_do_not_overlap():
    assert is_empty("check_base_vs_pared")


# --- removable ears: 8 sites (front and back; vertical by the floor edge, horizontal by the shell's side) ----
def test_ear_sites():
    sites = echo_values("echo_ears")["sites"]
    assert len(sites) == 8
    for f in ["front", "back"]:
        for m in ["vertical", "horizontal"]:
            assert sum(1 for s in sites if s[0] == f and s[1] == m) == 2


def test_lugs_coplanar_per_mode():
    v = echo_values("echo_ears")
    assert len(v["vertical_lug_planes"]) == 4 and len(v["horizontal_lug_planes"]) == 4
    assert all(abs(z) < 0.01 for z in v["vertical_lug_planes"])                # standing: lugs on the floor's plane
    assert all(abs(x - v["W"]) < 0.01 for x in v["horizontal_lug_planes"])     # lying on the shell's side
    assert v["lug_out"] >= 12                                                  # the lug sticks out this far


def test_base_has_no_fixed_ears(lay):
    lo, hi = stl_bbox(run_scad("base"))
    assert lo[1] >= -0.01 and hi[1] <= lay["D"] + 0.01


@pytest.mark.parametrize("c", ["check_pads_vs_ghosts", "check_ears_vs_power", "check_ears_vs_back"])
def test_ear_sites_clear(c):
    assert is_empty(c)


def test_ear_and_blank_flush_in_their_pocket():
    assert is_empty("check_ear_flush")             # ears in every site: nothing of base, face or shell; blanks flush


@pytest.mark.parametrize("p", ["ear", "ear_blank"])
def test_ear_prints_flat(p):
    lo, hi = stl_bbox(run_scad(p))
    assert lo[2] == pytest.approx(0, abs=0.01)


# --- shell ------------------------------------------------------------------------------------------
def test_shell_fits_assembled():
    assert is_empty("check_tapa_assembled")


@pytest.mark.parametrize("dz", [20, 60, 130])
def test_shell_slides_on_from_above(dz):
    assert is_empty("check_tapa_slide", {"dz": dz})


@pytest.mark.parametrize("g", ["pico", "pi", "conv", "xt60", "switch", "cables", "hdmi", "leds", "usb"])
def test_shell_clear_of_ghosts(g):
    assert is_empty("check_tapa_vs_ghost", {"ga": g})


def test_vents():
    v = echo_values("echo_vents")
    assert v["top_mm2"] >= 1000 and v["right_mm2"] >= 800 and v["front_mm2"] >= 300


def test_overall_size_and_volume():
    lo, hi = stl_bbox(run_scad("montaje_sin_orejetas"))
    size = [h - l for l, h in zip(lo, hi)]
    assert size == pytest.approx([62, 95, 145], abs=3)
    assert size[0] * size[1] * size[2] / 1e6 < 1.1          # litres: well under the first box's 1.78


# --- hardware ---------------------------------------------------------------------------------------
EXPECTED = {"ins_m3": 34, "ins_m25": 4, "m3x8_flat": 24, "m3x6_pan": 8, "m3x6_cyl": 2, "m3x10_flat": 0, "m3x10_pan": 2,
            "nut_m3": 2,
            "m25x6": 4, "m4x12": 4}


def test_bom_counts():
    v = echo_values("echo_bom")
    assert {k: v[k] for k in EXPECTED} == EXPECTED and v["inserts_without_screw"] == 0


@pytest.mark.parametrize("model", ["pi4", "pi5"])
@pytest.mark.parametrize("kind", ["ins_m3", "ins_m25", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_pan", "m25x6"])
def test_hardware_only_goes_through_holes(kind, model):
    assert is_empty("check_screws_vs_parts", {"kind": kind, "model": model})


# --- shell with a 30 mm fan over the Pi (shell_fan): inside or outside on the same holes ---------------------
GHOSTS = ["pico", "pi", "conv", "xt60", "switch", "cables", "hdmi", "leds", "usb"]


def test_shell_fan_fits_assembled():
    assert is_empty("check_tapa_fan_assembled")


@pytest.mark.parametrize("dz", [20, 60, 130])
def test_shell_fan_slides_on_from_above_with_the_fan_inside(dz):
    assert is_empty("check_tapa_fan_slide", {"dz": dz})


@pytest.mark.parametrize("g", GHOSTS)
def test_shell_fan_clear_of_ghosts(g):
    assert is_empty("check_tapa_fan_vs_ghost", {"ga": g})


# not the Pi's ghost: it is a solid block with 25 mm kept in front of the board for a fan, and this fan is that
@pytest.mark.parametrize("dz", [0, 30, 90])
@pytest.mark.parametrize("g", [g for g in GHOSTS if g != "pi"])
def test_fan_inside_clear_of_everything_while_the_shell_goes_on(g, dz):
    assert is_empty("check_fan_inside_vs_ghost", {"ga": g, "dz": dz})


def test_fan_sits_on_the_wall_inside_or_outside():
    assert is_empty("check_fan_vs_shell")


def test_fan_screw_holes_open_with_wall_round_them():
    assert is_empty("check_fan_holes_open")      # nothing in the holes
    assert is_empty("check_fan_hole_rims")       # 1 mm of wall all round each hole


def test_fan_over_the_pi_soc():
    v = echo_values("echo_fan")
    y, z = v["fan_c"]
    assert v["pi_y"][0] + 15 <= y <= v["pi_y"][1] - 15      # the whole fan in front of the board
    assert v["pi_z"][0] + 15 <= z <= v["pi_z"][1] - 15
    assert z + 15 < v["conv_z0"]                              # under the converter
    assert v["gap_inside"] >= 15                              # room between the fan inside and the Pi's parts
    assert v["open_to_hole"] >= 1.0                           # wall between the opening and each screw hole


def test_shell_fan_prints_like_the_shell():
    lo, hi = stl_bbox(run_scad("shell_fan"))
    lo0, hi0 = stl_bbox(run_scad("shell"))
    assert lo[2] == pytest.approx(0, abs=0.01)
    assert lo == pytest.approx(lo0, abs=0.01) and hi == pytest.approx(hi0, abs=0.01)


# --- IMU bracket on the Pi (one piece: the arm for the box lying, the shelf for the box standing) ----------
def test_imu_bracket_clear_of_the_box_and_the_fan():
    assert is_empty("check_imu_vs_box")


@pytest.mark.parametrize("g", [g for g in GHOSTS if g != "pi"])
def test_imu_bracket_clear_of_ghosts(g):
    assert is_empty("check_imu_vs_ghost", {"ga": g})


def test_imu_bracket_clear_of_the_pi_board_and_its_jacks():
    assert is_empty("check_imu_vs_pi_jacks")


@pytest.mark.parametrize("dz", [10, 40, 100])
def test_shell_fan_slides_past_the_imu_bracket(dz):
    assert is_empty("check_imu_shell_slide", {"dz": dz})


def test_imu_bracket_sits_on_its_standoffs():
    assert not is_empty("check_imu_standoffs_touch")


def test_imu_bracket_room():
    v = echo_values("echo_imu")
    assert v["shelf_top"] <= v["pi_z0"] - 1.5          # the shelf passes under the Pi's bottom edge
    assert v["shelf_board_bottom"] - 1.5 > v["floor"]   # the hanging board (+ its solder) clears the floor
    assert v["y"][0] > v["fan_y1"]                      # behind the fan


def test_imu_bracket_prints_on_its_end():
    lo, hi = stl_bbox(run_scad("imu_bracket"))
    assert lo[2] == pytest.approx(0, abs=0.01)
    assert hi[2] < 73.5 - 52.5 + 2          # the arm's end bosses stick out 1.4 at the top
