# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The collision helper: overlap is a collision, faces that only touch are not."""
from scad import is_empty


def test_touching_faces_are_not_a_collision():
    assert is_empty("check_selftest", {"gap": 0})


def test_overlap_is_a_collision():
    assert not is_empty("check_selftest", {"gap": -0.5})


def test_apart_is_empty():
    assert is_empty("check_selftest", {"gap": 1})
