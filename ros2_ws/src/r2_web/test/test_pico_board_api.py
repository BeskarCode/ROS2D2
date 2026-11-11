# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_web.pico_board_api import pico_board_payload, save_pico_board


def files(tmp_path):
    default = tmp_path / "pkg.yaml"
    default.write_text("brightness: 2\n", encoding="utf-8")
    return str(default), str(tmp_path / "user" / "pico_board.yaml")


def test_package_file_when_nothing_saved(tmp_path):
    default, user = files(tmp_path)
    p = pico_board_payload(default, user)
    assert p["saved"] is False and p["file"] == default and p["error"] is None
    assert p["settings"] == {"display_timeout_s": 30, "brightness": 2, "leds": "auto"}


def test_save_valid_and_it_wins(tmp_path):
    default, user = files(tmp_path)
    code, body = save_pico_board("display_timeout_s: 60\nbrightness: 3\nleds: errors\n", user)
    assert code == 200 and body["file"] == user
    p = pico_board_payload(default, user)
    assert p["saved"] is True and p["settings"] == {"display_timeout_s": 60, "brightness": 3, "leds": "errors"}


def test_save_invalid_is_refused_and_not_written(tmp_path):
    default, user = files(tmp_path)
    code, body = save_pico_board("brightness: 9\n", user)
    assert code == 400 and "brightness" in body["error"]
    assert not os.path.exists(user)
    assert save_pico_board(None, user)[0] == 400


def test_broken_saved_file_is_reported_not_raised(tmp_path):
    default, user = files(tmp_path)
    os.makedirs(os.path.dirname(user))
    with open(user, "w", encoding="utf-8") as f:
        f.write("leds: blink\n")
    p = pico_board_payload(default, user)
    assert p["settings"] is None and "leds" in p["error"] and p["yaml"] == "leds: blink\n"
