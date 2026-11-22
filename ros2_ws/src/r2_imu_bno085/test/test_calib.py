# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The correction from the chip's axes to R2's, levelling and the user file (pure, no ROS)."""

import math

import pytest

from r2_imu_bno085.calib import (DEFAULTS, Mount, check_setting, level_from, linear_accel, load_user,
                                 save_user)


def test_no_level_front_x_is_identity():
    m = Mount(None, "+x")
    assert m.to_r2(30, 4, -6) == pytest.approx((30, 4, -6), abs=1e-6)
    assert m.vec((1, 2, 3)) == pytest.approx((1, 2, 3))


def test_level_cancels_the_box_tilt():            # the ~10 deg the box sits at
    m = Mount({"roll_deg": -3.0, "pitch_deg": 10.0}, "+x")
    _, p, r = m.to_r2(50, 10.0, -3.0)
    assert (p, r) == pytest.approx((0, 0), abs=1e-6)


def test_level_cancels_the_upside_down_board():   # box lying: roll ~180
    m = Mount({"roll_deg": 179.0, "pitch_deg": 2.0}, "+x")
    _, p, r = m.to_r2(0, 2.0, 179.0)
    assert (p, r) == pytest.approx((0, 0), abs=1e-6)


def test_after_level_front_down_is_pitch_plus():
    m = Mount({"roll_deg": 0.0, "pitch_deg": 10.0}, "+x")
    assert m.to_r2(0, 15.0, 0)[1] == pytest.approx(5.0, abs=1e-6)


def test_front_plus_y_swaps_axes():               # R2's front is the chip's +y
    m = Mount(None, "+y")
    assert m.vec((0, 1, 0)) == pytest.approx((1, 0, 0), abs=1e-9)
    assert m.to_r2(0, 0, 5.0)[1] == pytest.approx(-5.0, abs=1e-6)   # chip roll is R2 pitch


def test_vec_matches_level():                     # gravity at level ends up straight up
    m = Mount({"roll_deg": 0.0, "pitch_deg": 10.0}, "+x")
    g = 9.80665
    s, c = math.sin(math.radians(10)), math.cos(math.radians(10))
    assert m.vec((-g * s, 0, g * c)) == pytest.approx((0, 0, g), abs=1e-6)


def test_linear_accel_still_is_zero():
    assert linear_accel(0, 0, (0, 0, 9.80665)) == pytest.approx((0, 0, 0), abs=1e-6)


def test_linear_accel_tilted_still_is_zero():
    g = 9.80665
    s, c = math.sin(math.radians(10)), math.cos(math.radians(10))
    assert linear_accel(10, 0, (-g * s, 0, g * c)) == pytest.approx((0, 0, 0), abs=1e-6)


def test_level_from_averages_across_the_wrap():
    lv, err = level_from([(179.5, 1.0), (-179.5, 1.0)] * 30)
    assert err == "" and abs(lv["roll_deg"]) == pytest.approx(180.0, abs=1e-6)


def test_level_from_needs_frames():
    assert level_from([])[0] is None and "no frames" in level_from([])[1]


def test_level_from_refuses_when_moving():
    lv, err = level_from([(0.0, 0.0)] * 30 + [(3.0, 0.0)] * 30)
    assert lv is None and "still" in err


@pytest.mark.parametrize("name,value", [("box", "sideways"), ("front", "z"), ("port", ""),
                                        ("in_use", "yes"), ("invert_yaw", 1), ("level", "x")])
def test_check_setting_rejects(name, value):
    assert check_setting(name, value) != ""


@pytest.mark.parametrize("name,value", [("box", "lying"), ("front", "-y"), ("port", "/dev/ttyAMA3"),
                                        ("in_use", False), ("invert_yaw", True), ("level", None),
                                        ("level", {"roll_deg": 1.0, "pitch_deg": 2})])
def test_check_setting_accepts(name, value):
    assert check_setting(name, value) == ""


def test_save_then_load(tmp_path):
    p = tmp_path / "ros2d2" / "imu.yaml"
    save_user(str(p), dict(DEFAULTS, box="lying", level={"roll_deg": 179.0, "pitch_deg": 2.0}))
    cfg, err = load_user(str(p))
    assert err == "" and cfg["box"] == "lying" and cfg["level"]["roll_deg"] == 179.0


def test_load_missing_file_is_defaults(tmp_path):
    assert load_user(str(tmp_path / "nope.yaml")) == (DEFAULTS, "")


def test_load_broken_yaml_gives_defaults_and_error(tmp_path):
    p = tmp_path / "imu.yaml"
    p.write_text("box: [unclosed")
    cfg, err = load_user(str(p))
    assert cfg == DEFAULTS and err


def test_load_bad_value_falls_back(tmp_path):
    p = tmp_path / "imu.yaml"
    p.write_text("box: sideways\nfront: -y\n")
    cfg, err = load_user(str(p))
    assert cfg["box"] == "standing" and cfg["front"] == "-y" and "box" in err
