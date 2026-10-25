import pytest

from r2_camera.config import load_cameras, node_params, spread


def write(tmp_path, text):
    p = tmp_path / "cameras.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_named_cameras_keep_their_order_and_get_defaults(tmp_path):
    cams = load_cameras(write(tmp_path, "left:\n  source: /dev/video0\n  yaw_deg: -30\nright:\n  source: 2\n"))
    assert list(cams) == ["left", "right"]
    assert cams["left"]["yaw_deg"] == -30 and cams["left"]["hfov_deg"] == 60.0
    assert cams["right"]["yaw_deg"] == 0.0


def test_auto_numbers_the_cameras_and_spreads_them(tmp_path):
    path = write(tmp_path, "auto:\n  hfov_deg: 70\n  spread_deg: 60\n  width: 640\n")
    cams = load_cameras(path, found=["/dev/v4l/by-path/port1", "/dev/v4l/by-path/port2"])
    assert list(cams) == ["cam1", "cam2"]
    assert cams["cam1"]["yaw_deg"] == pytest.approx(-30) and cams["cam2"]["yaw_deg"] == pytest.approx(30)
    assert cams["cam2"]["source"] == "/dev/v4l/by-path/port2"
    assert cams["cam1"]["hfov_deg"] == 70 and cams["cam1"]["width"] == 640


def test_auto_with_one_camera_looks_ahead(tmp_path):
    cams = load_cameras(write(tmp_path, "auto:\n"), found=["/dev/v4l/by-path/port1"])
    assert cams["cam1"]["yaw_deg"] == 0.0


def test_auto_with_no_camera_is_empty(tmp_path):
    assert load_cameras(write(tmp_path, "auto:\n"), found=[]) == {}


def test_spread_three():
    assert spread(3, 120) == [-60.0, 0.0, 60.0]


def test_node_params_drop_the_geometry():
    assert node_params({"source": 0, "yaw_deg": 5, "hfov_deg": 60, "width": 640}) == {"source": "0", "width": 640}
