# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/modes for Setup -> Modes: read and save modes.yaml (which combo starts each mode, and the
follow-a-colour settings). No ROS here, so it can be tested on its own; the web server tells the
Mega bridge and the mode nodes to re-read the file (/r2/modes/reload) after a save."""

import os
import tempfile

from r2_nav.modes import COMBOS, ModesConfigError, parse_modes


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
