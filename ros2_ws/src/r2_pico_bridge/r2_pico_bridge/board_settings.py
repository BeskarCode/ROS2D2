# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The Pico carrier board's settings (pico_board.yaml), kept on the Pi and sent to the Pico
by the bridge after every CFG and whenever the file changes (the Pico keeps none):

    display_timeout_s: 30     # 10, 30, 60, 300, or 0 = never off by itself
    brightness: 2             # 0-3
    leds: auto                # auto (only with the display on) | on | connected (only those measuring) | off | errors (only those failing)

Saved from the web console (System tab) in ~/.config/ros2d2/pico_board.yaml; when that file
exists it wins over the package's one. No ROS here: tested on its own."""

import os
import re

import yaml

USER_CONFIG = os.path.expanduser("~/.config/ros2d2/pico_board.yaml")
DEFAULTS = {"display_timeout_s": 30, "brightness": 2, "leds": "auto"}
TIMEOUTS = (10, 30, 60, 300, 0)
BRIGHTNESS = (0, 1, 2, 3)
LEDS = ("auto", "on", "connected", "off", "errors")
_LED_WORD = {"auto": "auto", "on": "on", "connected": "conn", "off": "off", "errors": "err"}
CONNECTORS = ("VL1", "VL2", "VL3", "VL4", "US1", "US2", "US3", "US4", "US5")
# What the console may ask the Pico to do now (through /pico/command): nothing else gets through
_COMMAND = re.compile(r"^(DISP (on|on all|off|on (%s))|ID (%s)|PRESS (short|long))$" % ("|".join(CONNECTORS), "|".join(CONNECTORS)))


class BoardSettingsError(ValueError):
    pass


def config_path(default):
    """The pico_board.yaml to use: the one saved from the web console, if any, else default."""
    return USER_CONFIG if os.path.isfile(USER_CONFIG) else default


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def parse(text):
    """The settings, with the defaults filled in. Raises BoardSettingsError with what is wrong."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise BoardSettingsError(f"YAML: {e}") from None
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise BoardSettingsError("pico_board.yaml must be settings (name: value)")
    for key in raw:
        if key not in DEFAULTS:
            raise BoardSettingsError(f"{key}: not a setting ({', '.join(DEFAULTS)})")
    s = {**DEFAULTS, **raw}
    if isinstance(s["leds"], bool):            # YAML reads a bare on / off as true / false
        s["leds"] = "on" if s["leds"] else "off"
    if not _int(s["display_timeout_s"]) or s["display_timeout_s"] not in TIMEOUTS:
        raise BoardSettingsError("display_timeout_s must be 10, 30, 60, 300 or 0 (never)")
    if not _int(s["brightness"]) or s["brightness"] not in BRIGHTNESS:
        raise BoardSettingsError("brightness must be 0, 1, 2 or 3")
    if s["leds"] not in LEDS:
        raise BoardSettingsError(f"leds must be one of {', '.join(LEDS)}")
    return s


def load(path):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def ui_line(s):
    """The UI line the Pico understands (no newline)."""
    return f"UI t={s['display_timeout_s']} b={s['brightness']} led={_LED_WORD[s['leds']]}"


def command_ok(line):
    """True for the actions the console may send: DISP on [all|<connector>], DISP off, ID <connector>,
    PRESS short|long."""
    return isinstance(line, str) and bool(_COMMAND.match(line))
