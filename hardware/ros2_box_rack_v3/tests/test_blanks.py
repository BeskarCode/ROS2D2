# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Blanks for the unused connectors: each plugs onto its header's pins and closes its strip of the bay flush,
without touching the wall nor the finger room of a Dupont plugged in next to it."""
import pytest

from scad import echo_values, is_empty, run_scad, stl_bbox, stl_volume

N = 10   # US1-US5, VL1-VL4, EXP


@pytest.fixture(scope="module")
def lay():
    return echo_values("echo_blanks")


def test_one_blank_per_connector(lay):
    assert lay["blank_names"] == ["US1", "US2", "US3", "US4", "US5", "VL1", "VL2", "VL3", "VL4", "EXP"]


@pytest.mark.parametrize("i", range(N))
@pytest.mark.parametrize("leds", [0, 1])
def test_blank_vs_wall(i, leds):
    assert is_empty("check_blank_vs_wall", {"bi": i, "leds": leds})


@pytest.mark.parametrize("i", range(N))
def test_blank_leaves_neighbour_pinch(i):
    # a Dupont plugged into any other connector keeps its 2.5 mm per side for the fingers
    assert is_empty("check_blank_pinch", {"bi": i})


@pytest.mark.parametrize("i", range(N))
def test_pin_holes_on_pins(i):
    assert is_empty("check_blank_pins", {"bi": i})


@pytest.mark.parametrize("i", range(N))
def test_blank_print_orientation(i, lay):
    lo, hi = stl_bbox(run_scad("blank", {"bi": i}))
    assert lo[2] == pytest.approx(0, abs=0.01)                                  # outer face on the bed
    assert hi[2] == pytest.approx(lay["pico_x"] - 2.5 - lay["blank_air"], abs=0.01)   # stem stops short of the header


def test_full_set_closes_bays():
    # seen through the wall's thickness, the bays minus all ten blanks: only the seams and the fit are left
    left = stl_volume(run_scad("check_bays_open_with_blanks"))
    bays = stl_volume(run_scad("bays_slab"))
    assert 0 < left < 0.15 * bays


def test_blanks_plate_renders():
    lo, hi = stl_bbox(run_scad("blanks_all"))
    assert lo[2] == pytest.approx(0, abs=0.01) and hi[0] - lo[0] < 180 and hi[1] - lo[1] < 180


def test_blanks_go_in_their_own_folder(tmp_path):
    import importlib.util
    from scad import HERE
    spec = importlib.util.spec_from_file_location("build_rack_v3", HERE / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert build.stl_path(tmp_path, "blank_VL3") == tmp_path / "stl" / "blanks" / "blank_VL3.stl"
    assert build.stl_path(tmp_path, "blanks_all") == tmp_path / "stl" / "blanks" / "blanks_all.stl"
    assert len(build.BLANK_NAMES) == 10


@pytest.mark.parametrize("name", ["README.md", "README_es.md"])
def test_readme_lists_the_blanks(name):
    from scad import HERE
    assert "stl/blanks/blank_US1.stl" in (HERE / name).read_text(encoding="utf-8")
