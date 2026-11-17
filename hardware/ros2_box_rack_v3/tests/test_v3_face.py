# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""v3 main face: flat, the board 14 mm behind it, a bay over each group of connectors so every Dupont plugs
in from outside, no sensor slot, no connector names, a second top insert."""
import pytest

from scad import HERE, echo_values, is_empty


@pytest.fixture(scope="module")
def lay():
    return echo_values("echo_layout")


def test_box_is_narrower(lay):
    assert lay["W"] == pytest.approx(62, abs=0.01)
    assert lay["pico_gap"] == pytest.approx(14, abs=0.01)


@pytest.mark.parametrize("leds", [0, 1])
def test_dupont_plugs_pass_through_their_bays(leds):
    # every mated Dupont housing, from the board out through the face and 20 mm beyond: nothing of the face
    assert is_empty("check_bay_vs_dupont", {"leds": leds})


def test_bays_leave_pinch_room():
    # 2.5 mm on both long sides of every housing, from outside down to 3 mm into the box: free for the fingers
    assert is_empty("check_bay_vs_pinch")


def test_bays_keep_the_led_tubes_whole():
    assert is_empty("check_bay_vs_tubes")


def test_bays_keep_columns_window_and_rod_guide():
    assert is_empty("check_bay_vs_keepouts")


def test_no_sensor_slot_and_no_labels():
    src = "".join(f.read_text(encoding="utf-8") for f in HERE.glob("*.scad"))
    assert "sensor_slot" not in src and "lp_label" not in src


def test_two_top_tabs(lay):
    assert lay["top_tab_y"] == [75, 20]


# --- Task 3: the board lower, a straight micro-USB ------------------------------------------------
def test_usb_room_is_a_parameter_at_30(lay):
    assert lay["pico_usb_clear"] == pytest.approx(30, abs=0.01)


def test_board_above_the_bottom_tabs(lay):
    assert lay["pico_zbot"] >= lay["wall"] + 8 + 1      # tab height 8 + 1 air


def test_straight_usb_clears_roof(lay):
    assert is_empty("check_usb_vs_shell")


@pytest.mark.parametrize("leds", [0, 1])
def test_straight_usb_clears_the_face(leds):
    assert is_empty("check_usb_vs_pared", {"leds": leds})


def test_logo_clear_of_the_usb_recess():
    assert is_empty("check_logo_vs_usb_recess")
