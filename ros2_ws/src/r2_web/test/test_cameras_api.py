# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_camera.config import load_cameras
from r2_web.cameras_api import save_cameras

GOOD = "cam1:\n  source: /dev/video0\n  yaw_deg: 10\n"


def test_saved_whole_and_readable(tmp_path):
    user = str(tmp_path / "cfg" / "cameras.yaml")
    code, body = save_cameras({"yaml": GOOD}, user)
    assert code == 200 and body["file"] == user
    assert load_cameras(user)["cam1"]["yaw_deg"] == 10
    assert not os.path.exists(user + ".tmp")


def test_a_bad_file_leaves_the_old_one_alone(tmp_path):
    user = str(tmp_path / "cameras.yaml")
    assert save_cameras({"yaml": GOOD}, user)[0] == 200
    for bad in ({"yaml": "- a\n- b\n"}, {"yaml": "cam1: [1, 2\n"}, {"yaml": "cam1: 3\n"}, {"yaml": 5}, {}):
        code, body = save_cameras(bad, user)
        assert code == 400, bad
        assert body["error"].startswith("not saved")
    assert load_cameras(user)["cam1"]["yaw_deg"] == 10
    assert not os.path.exists(user + ".tmp")


def test_a_body_that_is_not_an_object_is_refused(tmp_path):
    for bad in ([1, 2], "text", None, 7):
        assert save_cameras(bad, str(tmp_path / "c.yaml"))[0] == 400
