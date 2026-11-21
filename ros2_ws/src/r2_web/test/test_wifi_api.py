# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import json

from r2_web.wifi_api import NOT_INSTALLED, last_pick, move, survey


def test_last_pick_reads_the_state(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"channel": 11, "was": 6, "busy_dbm": {"1": -29.0, "6": -22.9, "11": -80.5}}))
    code, body = last_pick(str(p))
    assert code == 200 and body["pick"]["channel"] == 11


def test_last_pick_before_any_says_how_to_install(tmp_path):
    assert last_pick(str(tmp_path / "none.json")) == (200, {"pick": None, "error": NOT_INSTALLED})


def test_survey_parses_the_helper_line():
    line = json.dumps({"channel": 11, "best": 11, "busy_dbm": {"1": -29.0}})
    code, body = survey(lambda cmd: (0, line))
    assert code == 200 and body["survey"]["best"] == 11


def test_survey_without_sudoers_rule():
    assert survey(lambda cmd: (1, "sudo: a password is required")) == (409, {"error": NOT_INSTALLED})


def test_move_restarts_hostapd(tmp_path, monkeypatch):
    seen = []
    import r2_web.wifi_api as w
    monkeypatch.setattr(w, "STATE", str(tmp_path / "s.json"))
    (tmp_path / "s.json").write_text(json.dumps({"channel": 1}))
    code, body = move(lambda cmd, timeout=60: (seen.append(cmd), (0, ""))[1])
    assert seen == [["sudo", "-n", "systemctl", "restart", "hostapd"]]
    assert code == 200
