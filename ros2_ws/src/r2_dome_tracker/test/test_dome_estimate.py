import pytest

from r2_dome_tracker.control import DomeEstimate, simulated_error


def test_positive_speed_turns_right_without_invert():
    d = DomeEstimate(deg_per_s_at_80=90.0)
    d.update(speed=80, invert=False, dt=1.0)
    assert d.angle == pytest.approx(90.0)


def test_invert_flips_the_direction():
    # invert means a negative DM: speed turns the dome right on this droid
    d = DomeEstimate(deg_per_s_at_80=90.0)
    d.update(speed=-40, invert=True, dt=1.0)
    assert d.angle == pytest.approx(45.0)


def test_angle_wraps_to_plus_minus_180():
    d = DomeEstimate(deg_per_s_at_80=90.0)
    d.update(speed=80, invert=False, dt=2.5)       # 225 degrees right = 135 left
    assert d.angle == pytest.approx(-135.0)


def test_reset():
    d = DomeEstimate(deg_per_s_at_80=90.0)
    d.update(speed=80, invert=False, dt=1.0)
    d.reset()
    assert d.angle == 0.0


def test_dome_turned_towards_the_face_centres_it():
    # Face at the right edge of a 60 degree camera = 30 degrees right of the dome
    assert simulated_error(1.0, dome_deg=30.0, hfov_deg=60.0) == pytest.approx(0.0)
    assert simulated_error(1.0, dome_deg=15.0, hfov_deg=60.0) == pytest.approx(0.5)


def test_dome_turned_past_the_face_puts_it_on_the_other_side():
    assert simulated_error(0.0, dome_deg=15.0, hfov_deg=60.0) == pytest.approx(-0.5)


def test_face_out_of_the_simulated_view():
    assert simulated_error(-1.0, dome_deg=40.0, hfov_deg=60.0) is None
