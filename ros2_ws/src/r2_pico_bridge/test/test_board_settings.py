# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import pytest

from r2_pico_bridge.board_settings import DEFAULTS, BoardSettingsError, command_ok, parse, ui_line


def test_defaults_are_todays_behaviour():
    assert DEFAULTS == {"display_timeout_s": 30, "brightness": 2, "leds": "auto"}
    assert parse("") == DEFAULTS
    assert parse("brightness: 3\n") == {**DEFAULTS, "brightness": 3}


def test_valid_values():
    s = parse("display_timeout_s: 0\nbrightness: 0\nleds: errors\n")
    assert s == {"display_timeout_s": 0, "brightness": 0, "leds": "errors"}
    for t in (10, 30, 60, 300, 0):
        assert parse(f"display_timeout_s: {t}\n")["display_timeout_s"] == t
    for led in ("auto", "on", "off", "errors", "connected"):
        assert parse(f"leds: {led}\n")["leds"] == led


@pytest.mark.parametrize("text, msg", [
    ("display_timeout_s: 45\n", "display_timeout_s"),
    ("brightness: 4\n", "brightness"),
    ("brightness: true\n", "brightness"),
    ("leds: blink\n", "leds"),
    ("colour: red\n", "colour"),
    ("- a list\n", "settings"),
    ("leds: [\n", "YAML"),
])
def test_invalid_values(text, msg):
    with pytest.raises(BoardSettingsError, match=msg):
        parse(text)


def test_ui_line():
    assert ui_line(DEFAULTS) == "UI t=30 b=2 led=auto"
    assert ui_line({"display_timeout_s": 0, "brightness": 3, "leds": "errors"}) == "UI t=0 b=3 led=err"
    assert ui_line({**DEFAULTS, "leds": "connected"}) == "UI t=30 b=2 led=conn"


def test_commands_the_console_may_send():
    for ok in ("DISP on", "DISP on all", "DISP on US3", "DISP off", "ID VL1", "ID US5"):
        assert command_ok(ok), ok
    for bad in ("DISP on XX", "DISP", "ID VL9", "ID", "BOOT", "CFG", "TM 1", "UI t=30", "DISP off\nBOOT"):
        assert not command_ok(bad), bad


def test_the_console_may_press_the_button():
    assert command_ok("PRESS short") and command_ok("PRESS long")
    for bad in ("PRESS", "PRESS x", "PRESS short\nBOOT", "MIR 1"):
        assert not command_ok(bad), bad
