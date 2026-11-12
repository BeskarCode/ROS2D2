# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The camera's :82/faces lines (components/r2_detect/faces_line.c), built on the PC and read
with the Pi's parser (r2_vision/remote_faces.py)."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "ros2_ws", "src", "r2_vision"))
sys.path.insert(0, HERE)

from cbuild import build, run   # noqa: E402
from r2_vision.remote_faces import parse_line   # noqa: E402


@pytest.fixture(scope="module")
def cli(tmp_path_factory):
    return build(tmp_path_factory.mktemp("c"), "line_cli",
                 ["line_cli.c", "../components/r2_detect/faces_line.c"])


def test_faces_line_is_read_by_the_pi(cli):
    line = run(cli, ["faces"]).rstrip("\n")
    assert "\n" not in line
    d = parse_line(line)
    assert d["mode"] == "faces" and d["marker"] is None
    assert d["w"] == 640 and d["h"] == 480 and d["rot"] == 90 and d["lat_ms"] == 48
    assert d["faces"] == [(10, 20, 30, 40, 0.91), (100, 120, 50, 60, 0.5)]


def test_colour_line_with_blob(cli):
    d = parse_line(run(cli, ["color"]))
    assert d["mode"] == "color" and d["faces"] == []
    assert d["marker"] == pytest.approx((0.25, 0.5, 0.012), abs=1e-3)


def test_colour_line_without_blob(cli):
    d = parse_line(run(cli, ["color_none"]))
    assert d["mode"] == "color" and d["marker"] is None


def test_small_buffer_is_refused(cli):
    assert run(cli, ["small"]).strip() == "-1"
