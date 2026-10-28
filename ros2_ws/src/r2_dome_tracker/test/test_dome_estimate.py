# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import pytest

from r2_dome_tracker.control import DomeEstimate, bearing_deg, face_to_error, in_view, pick_face


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


CAMS = [(-30.0, 60.0), (30.0, 60.0)]    # left and right, 60 deg each: -60..+60 covered


def test_bearing_from_each_camera():
    assert bearing_deg(0.0, -30.0, 60.0) == pytest.approx(-30.0)      # centre of the left camera
    assert bearing_deg(1.0, 30.0, 60.0) == pytest.approx(60.0)        # right edge of the right one
    assert bearing_deg(-1.0, 30.0, 60.0) == pytest.approx(0.0)        # where the two meet


def test_in_view_covers_both_cameras():
    assert in_view(-55.0, CAMS) and in_view(0.0, CAMS) and in_view(59.0, CAMS)
    assert not in_view(70.0, CAMS)


def test_pick_the_biggest_recent_face():
    latest = {"cam1": (10.0, -40.0, 0.10), "cam2": (10.0, 20.0, 0.25)}
    assert pick_face(latest, now=10.1, max_age=0.2) == (10.0, 20.0)


def test_old_faces_are_ignored():
    latest = {"cam1": (10.0, -40.0, 0.10), "cam2": (9.0, 20.0, 0.25)}
    assert pick_face(latest, now=10.1, max_age=0.2) == (10.0, -40.0)
    assert pick_face({"cam1": None}, now=10.0, max_age=0.2) is None


def test_error_is_degrees_over_30():
    assert face_to_error(15.0, 0.0, CAMS, simulate=False) == pytest.approx(0.5)
    assert face_to_error(60.0, 0.0, CAMS, simulate=False) == pytest.approx(2.0)


def test_simulate_shifts_by_the_dome_angle():
    # Face 24 deg right, virtual dome already turned 20: 4 deg left to go
    assert face_to_error(24.0, 20.0, CAMS, simulate=True) == pytest.approx(4.0 / 30)


def test_simulate_drops_faces_the_turned_cameras_would_not_see():
    # Dome turned 90 deg right: a face at -40 is 130 deg off, out of both cameras
    assert face_to_error(-40.0, 90.0, CAMS, simulate=True) is None
