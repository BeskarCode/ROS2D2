# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/remote: remote.yaml for the Remote window and the phone view (stick limit, guest, favourites)."""

from r2_shadow_bridge.remote_cfg import DEFAULTS
from r2_web.remote_api import remote_payload, save_remote


def test_payload_without_a_file(tmp_path):
    p = remote_payload(str(tmp_path / "remote.yaml"))
    assert p["remote"] == DEFAULTS and p["saved"] is False and p["error"] is None
    assert "stick_limit_pct: 20" in p["yaml"]


def test_a_bad_file_is_not_saved(tmp_path):
    user = tmp_path / "remote.yaml"
    user.write_text("stick_limit_pct: 30\n", encoding="utf-8")
    code, body = save_remote("stick_limit_pct: 500\n", str(user))
    assert code == 400 and "stick_limit_pct" in body["error"]
    assert user.read_text(encoding="utf-8") == "stick_limit_pct: 30\n"
    code, body = save_remote(42, str(user))
    assert code == 400


def test_save_and_read_back(tmp_path):
    user = tmp_path / "cfg" / "remote.yaml"
    code, body = save_remote("stick_limit_pct: 35\nguest: true\nfavorites: [{combo: FOOT_UP, name: Scream}]", str(user))
    assert code == 200 and body["file"] == str(user)
    p = remote_payload(str(user))
    assert p["saved"] is True and p["remote"]["stick_limit_pct"] == 35 and p["remote"]["guest"] is True
    assert p["remote"]["favorites"] == [{"combo": "FOOT_UP", "name": "Scream"}]


def test_a_broken_file_reads_as_defaults_with_its_error(tmp_path):
    user = tmp_path / "remote.yaml"
    user.write_text("stick_limit_pct: [", encoding="utf-8")
    p = remote_payload(str(user))
    assert p["remote"] == DEFAULTS and p["error"]
