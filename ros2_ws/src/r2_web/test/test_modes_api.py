# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_nav.modes import COMBOS, parse_modes
from r2_web.modes_api import modes_payload, save_modes

GOOD = "follow: {combo: FOOT_UP_PS}\n"
BAD = "follow: {combo: DOME_PS_L2}\n"
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "modes_from_form.yaml")


def files(tmp_path):
    default = tmp_path / "pkg.yaml"
    default.write_text("", encoding="utf-8")
    return str(default), str(tmp_path / "user" / "modes.yaml")


def test_payload_defaults(tmp_path):
    default, user = files(tmp_path)
    p = modes_payload(default, user)
    assert p["saved"] is False and p["file"] == default and p["error"] is None
    assert p["modes"]["goto"]["combo"] == "FOOT_PS_L2" and p["modes"]["follow"]["color"] is None
    assert p["combos"] == list(COMBOS) and len(p["combos"]) == 61


def test_saved_file_wins(tmp_path):
    default, user = files(tmp_path)
    assert save_modes(GOOD, user)[0] == 200
    p = modes_payload(default, user)
    assert p["saved"] is True and p["modes"]["follow"]["combo"] == "FOOT_UP_PS"


def test_broken_saved_file_is_reported(tmp_path):
    default, user = files(tmp_path)
    os.makedirs(os.path.dirname(user))
    with open(user, "w", encoding="utf-8") as f:
        f.write(BAD)
    p = modes_payload(default, user)
    assert p["modes"] == {} and "DOME_PS_L2" in p["error"] and p["yaml"] == BAD


def test_save_rejects_bad(tmp_path):
    _, user = files(tmp_path)
    save_modes(GOOD, user)
    code, body = save_modes(BAD, user)
    assert code == 400 and body["error"].startswith("not saved: follow.combo")
    assert save_modes("goto: {combo: FOOT_UP}\nfollow: {combo: FOOT_UP}\n", user)[0] == 400
    assert save_modes(123, user)[0] == 400
    with open(user, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_save_atomic(tmp_path):
    _, user = files(tmp_path)
    save_modes(GOOD, user)
    save_modes(GOOD.rstrip("\n"), user)
    assert os.listdir(os.path.dirname(user)) == ["modes.yaml"]


def test_the_form_writes_a_valid_file():
    # The same file modesform.test.mjs checks toYaml() against
    with open(FIXTURE, encoding="utf-8") as f:
        cfg = parse_modes(f.read())
    assert cfg["follow"]["combo"] == "FOOT_UP_PS" and cfg["patrol"]["combo"] == "DOME_LEFT_L2_CROSS"
    assert cfg["follow"]["color"] == {"h": 104, "s": 201, "v": 88}
    assert cfg["follow"]["area_ref"] == 0.07123 and cfg["follow"]["max_speed"] == 0.25
    assert cfg["forward"]["sound_on"] == "MD:$PS1" and cfg["goto"]["combo"] == "FOOT_PS_L2"
