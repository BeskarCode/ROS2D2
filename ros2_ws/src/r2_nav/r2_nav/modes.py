# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""modes.yaml: the controller combination that starts each mode and the mode's settings.

The Mega only knows the combo -> mode table (the Mega bridge sends it with ROS:BIND:); the rest
(sounds, the follow-a-colour settings) stay on the Pi. The 61 combo names are the firmware's
ROS_COMBO_NAMES, in the same order. DOME_PS_L2 is face tracking and is not a combo here.
"""

import copy
import math
import os

import yaml

from r2_nav.nav_core import SOUND

USER_MODES = os.path.expanduser("~/.config/ros2d2/modes.yaml")
MODES = ("goto", "forward", "patrol", "follow")
_DIRS = ("UP", "DOWN", "LEFT", "RIGHT")
COMBOS = (("FOOT_PS_L2",)
          + tuple(f"FOOT_{d}{s}" for d in _DIRS for s in ("", "_CROSS", "_CIRCLE", "_L1", "_PS", "_L3"))
          + tuple(f"DOME_{d}{s}" for d in _DIRS
                  for s in ("", "_CROSS", "_CIRCLE", "_L1", "_PS", "_L3", "_L2", "_L2_CROSS", "_L2_CIRCLE")))

_COMMON = {"combo": None, "sound_on": "", "sound_off": ""}
DEFAULTS = {
    "goto": dict(_COMMON, combo="FOOT_PS_L2"),
    "forward": dict(_COMMON),
    "patrol": dict(_COMMON),
    "follow": dict(_COMMON, sound_on="S1:$12", sound_off="S1:$13", sound_lost="S1:$22", camera="cam1",
                   color=None, hue_tol=12, light_tol=70, area_ref=None, distance=1.5, max_speed=0.3,
                   search_s=5),
}
FOLLOW_RANGES = {"hue_tol": (2, 40), "light_tol": (10, 120), "distance": (0.8, 4), "max_speed": (0.05, 0.4),
                 "search_s": (0, 20)}
_COLOR_MAX = {"h": 179, "s": 255, "v": 255}
_SOUNDS = ("sound_on", "sound_off", "sound_lost")


class ModesConfigError(ValueError):
    pass


def _number(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def parse_modes(text):
    """modes.yaml -> {mode: settings} with the defaults filled in. Raises ModesConfigError naming the key."""
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ModesConfigError(f"YAML: {e}") from None
    if not isinstance(raw, dict):
        raise ModesConfigError("modes.yaml must be a list of mode: settings")
    cfg = copy.deepcopy(DEFAULTS)
    for mode, block in raw.items():
        if mode not in MODES:
            raise ModesConfigError(f"{mode}: unknown mode")
        if block is None:
            continue
        if not isinstance(block, dict):
            raise ModesConfigError(f"{mode}: must be a block of key: value")
        for k, v in block.items():
            if k not in DEFAULTS[mode]:
                raise ModesConfigError(f"{mode}.{k}: unknown setting")
            cfg[mode][k] = v
    seen = {}
    for mode in MODES:
        c = cfg[mode]
        combo = c["combo"]
        if combo is not None:
            if combo == "DOME_PS_L2":
                raise ModesConfigError(f"{mode}.combo: DOME_PS_L2 is face tracking, it cannot be assigned")
            if combo not in COMBOS:
                raise ModesConfigError(f"{mode}.combo: unknown combo {combo!r}")
            if combo in seen:
                raise ModesConfigError(f"{mode}.combo: {combo} is already used by {seen[combo]}")
            seen[combo] = mode
        for k in _SOUNDS:
            if k in c:
                if c[k] is None:
                    c[k] = ""
                if not isinstance(c[k], str) or (c[k] and not SOUND.match(c[k])):
                    raise ModesConfigError(f"{mode}.{k}: must be empty or a command like S1:$12")
    f = cfg["follow"]
    for k, (lo, hi) in FOLLOW_RANGES.items():
        if not _number(f[k]) or not lo <= f[k] <= hi:
            raise ModesConfigError(f"follow.{k}: must be a number from {lo} to {hi}")
    if not isinstance(f["camera"], str) or not f["camera"]:
        raise ModesConfigError("follow.camera: must be a camera name")
    if f["color"] is not None:
        c = f["color"]
        if (not isinstance(c, dict) or set(c) != set(_COLOR_MAX)
                or not all(_number(c[k]) and 0 <= c[k] <= _COLOR_MAX[k] for k in _COLOR_MAX)):
            raise ModesConfigError("follow.color: must be null or {h: 0-179, s: 0-255, v: 0-255}")
        f["color"] = {k: int(c[k]) for k in _COLOR_MAX}
    if f["area_ref"] is not None and (not _number(f["area_ref"]) or not 0 < f["area_ref"] <= 1):
        raise ModesConfigError("follow.area_ref: must be null or a fraction above 0 up to 1")
    return cfg


def load_modes(path):
    with open(path, encoding="utf-8") as f:
        return parse_modes(f.read())


def bindings(cfg):
    """{combo: mode} for the modes that have a combo."""
    return {cfg[m]["combo"]: m for m in MODES if cfg[m]["combo"] is not None}


def modes_path(default):
    """~/.config/ros2d2/modes.yaml wins over the installed one (same pattern as nav.yaml)."""
    return USER_MODES if os.path.isfile(USER_MODES) else default


def drives_in(mode, mine):
    """Does the node of mode `mine` move the droid when /r2/mode says `mode`? None = the mode has
    not arrived (an old bridge never sends it): the navigator then counts as goto, as before."""
    if mode is None:
        return mine == "goto"
    return mode == mine


NAV_MODES = ("goto", "forward", "patrol")       # the modes the navigator drives (follow has its own node)


def nav_mode(mode):
    """Which of NAV_MODES the navigator runs for /r2/mode, or None when another node drives.
    None (an old bridge) and "" (autonomous mode off) count as goto, as before."""
    if not mode:
        return "goto"
    return mode if mode in NAV_MODES else None
