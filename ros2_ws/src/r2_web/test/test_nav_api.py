import os

from r2_web.nav_api import nav_payload, save_nav

GOOD = "max_speed: 0.3\n"
BAD = "max_speed: 9\n"


def files(tmp_path):
    default = tmp_path / "pkg.yaml"
    default.write_text("", encoding="utf-8")
    return str(default), str(tmp_path / "user" / "nav.yaml")


def test_package_file_when_nothing_saved(tmp_path):
    default, user = files(tmp_path)
    p = nav_payload(default, user)
    assert p["saved"] is False and p["file"] == default and p["error"] is None
    assert p["nav"]["max_turn_deg"] == 30


def test_saved_file_wins(tmp_path):
    default, user = files(tmp_path)
    assert save_nav(GOOD, user)[0] == 200
    p = nav_payload(default, user)
    assert p["saved"] is True and p["nav"]["max_speed"] == 0.3


def test_broken_saved_file_is_reported(tmp_path):
    default, user = files(tmp_path)
    os.makedirs(os.path.dirname(user))
    with open(user, "w", encoding="utf-8") as f:
        f.write(BAD)
    p = nav_payload(default, user)
    assert p["nav"] == {} and "max_speed" in p["error"]


def test_bad_save_keeps_the_old_file(tmp_path):
    _, user = files(tmp_path)
    save_nav(GOOD, user)
    code, body = save_nav(BAD, user)
    assert code == 400 and body["error"].startswith("not saved: max_speed")
    with open(user, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_save_is_atomic(tmp_path):
    _, user = files(tmp_path)
    save_nav(GOOD, user)
    assert os.listdir(os.path.dirname(user)) == ["nav.yaml"]


def test_save_refuses_non_text(tmp_path):
    _, user = files(tmp_path)
    assert save_nav(123, user)[0] == 400
