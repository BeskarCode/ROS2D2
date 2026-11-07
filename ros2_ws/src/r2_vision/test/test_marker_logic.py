import json

import numpy as np

from r2_vision.color_marker import Marker
from r2_vision.marker_logic import detect_value, marker_json, parse_pick, pick_result, wants_video


def orange_picture():
    img = np.full((120, 160, 3), 90, np.uint8)
    img[40:80, 60:100] = (0, 128, 255)   # BGR orange
    return img


def test_wants_video():
    assert wants_video("follow", False) and wants_video("", True) and wants_video("goto", True)
    assert not wants_video("", False) and not wants_video("patrol", False)


def test_detect_value():
    assert detect_value("", "follow", True) == 0
    assert detect_value("follow", "", True) == 1
    assert detect_value("follow", "goto", True) == 1
    assert detect_value("goto", "follow", True) == 0
    assert detect_value("goto", "patrol", True) is None
    assert detect_value("follow", "follow", True) is None
    assert detect_value("", "follow", False) is None


def test_parse_pick_clamps_and_rejects():
    assert parse_pick('{"x":1.5,"y":-0.2,"hue_tol":12,"light_tol":70}') == (1.0, 0.0, 12, 70)
    assert parse_pick("nope") is None
    assert parse_pick('{"x":0.5}') is None
    assert parse_pick('{"x":NaN,"y":0.5,"hue_tol":1,"light_tol":1}') is None


def test_parse_pick_survives_overflow_and_clamps_tolerances():
    assert parse_pick('{"x":0.5,"y":0.5,"hue_tol":Infinity,"light_tol":1}') is None
    assert parse_pick('{"x":1' + "0" * 400 + ',"y":0.5,"hue_tol":12,"light_tol":70}') is None
    assert parse_pick('{"x":0.5,"y":0.5,"hue_tol":999,"light_tol":-5}') == (0.5, 0.5, 40, 10)


def test_pick_result_on_orange():
    r = pick_result(orange_picture(), 0.5, 0.5, 12, 70)
    assert r["warning"] is None and r["match"] > 0.05 and r["area"] > 0.05
    assert r["rgb"] == [255, 128, 0] and 0 <= r["h"] <= 179


def test_pick_result_corner_does_not_crash():
    r = pick_result(orange_picture(), 1.0, 1.0, 12, 70)
    assert r["rgb"] == [90, 90, 90] and r["warning"] == "too pale"


def test_marker_json():
    d = json.loads(marker_json(Marker(0.25, 0.5, 0.1), 60.0, 12.5))
    assert d["seen"] and d["bearing"] > 0 and d["area"] == 0.1 and d["t"] == 12.5
    d = json.loads(marker_json(None, 60.0, 1.0))
    assert d["seen"] is False and d["area"] == 0.0
