# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/modes for Setup -> Modes: read and save modes.yaml (which combo starts each mode, and the
follow-a-colour settings). No ROS here, so it can be tested on its own; the web server tells the
Mega bridge and the mode nodes to re-read the file (/r2/modes/reload) after a save."""

import os
import tempfile

import yaml

from r2_nav.modes import COMBOS, MODES, ModesConfigError, parse_modes


def modes_payload(default, user):
    """What the Modes tab loads, with the combo names it may offer. A broken file comes back as
    `error`, never raises."""
    path = user if os.path.isfile(user) else default
    out = {"file": path, "saved": path == user, "yaml": "", "modes": {}, "error": None, "combos": list(COMBOS)}
    try:
        with open(path, encoding="utf-8") as f:
            out["yaml"] = f.read()
    except OSError as e:
        out["error"] = f"{path}: {e.strerror}"
        return out
    try:
        out["modes"] = parse_modes(out["yaml"])
    except ModesConfigError as e:
        out["error"] = str(e)
    return out


def save_modes(text, user):
    """(HTTP code, body). Only a valid file is written, in one go (never half a file)."""
    if not isinstance(text, str):
        return 400, {"error": "not saved: the body must carry the file as text"}
    try:
        parse_modes(text)
    except ModesConfigError as e:
        return 400, {"error": f"not saved: {e}"}
    folder = os.path.dirname(user)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".modes-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user}


START_COMBO = "FOOT_PS_L2"     # what the Console / Navigation mode buttons choose the mode of


def set_start_mode(default, user, mode):
    """(HTTP code, body). Make PS + L2 (foot Nav) start `mode`: it takes PS + L2 and the mode that
    had it gets `mode`'s old combo (swapped, so no combo is lost). Saved to `user` like a save
    from the Modes tab; the Mega still needs the controller to switch the mode on."""
    if mode not in MODES:
        return 400, {"error": f"not saved: mode must be one of {', '.join(MODES)}"}
    p = modes_payload(default, user)
    if p["error"]:
        return 400, {"error": f"not saved: {p['error']}"}
    cfg = p["modes"]
    holder = next((m for m in MODES if cfg[m]["combo"] == START_COMBO), None)
    if holder != mode:
        if holder is not None:
            cfg[holder]["combo"] = cfg[mode]["combo"]
        cfg[mode]["combo"] = START_COMBO
    text = ("# ROS2D2 modes (saved from the web console). combo: which controller combination starts\n"
            "# each mode (null = none); DOME_PS_L2 is face tracking and cannot be assigned.\n"
            + yaml.safe_dump({m: cfg[m] for m in MODES}, sort_keys=False, default_flow_style=None))
    code, body = save_modes(text, user)
    if code == 200:
        body["start"] = mode
    return code, body
