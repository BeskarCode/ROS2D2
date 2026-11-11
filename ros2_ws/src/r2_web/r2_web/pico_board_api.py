# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/pico_board for the System tab: read and save pico_board.yaml (the Pico carrier board's
display timeout, brightness and LED mode). The bridge sees the saved file and sends it to the
Pico at once. No ROS here, so it can be tested on its own."""

import os
import tempfile

from r2_pico_bridge.board_settings import BoardSettingsError, parse


def pico_board_payload(default, user):
    """What the System tab loads. A broken file comes back as `error`, never raises."""
    path = user if os.path.isfile(user) else default
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return {"file": path, "saved": path == user, "yaml": "", "settings": None, "error": f"{path}: {e.strerror}"}
    try:
        settings, error = parse(text), None
    except BoardSettingsError as e:
        settings, error = None, str(e)
    return {"file": path, "saved": path == user, "yaml": text, "settings": settings, "error": error}


def save_pico_board(text, user):
    """(HTTP code, body). Only a valid file is written, in one go (never half a file)."""
    if not isinstance(text, str):
        return 400, {"error": "not saved: the body must carry the file as text"}
    try:
        parse(text)
    except BoardSettingsError as e:
        return 400, {"error": f"not saved: {e}"}
    folder = os.path.dirname(user)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".pico_board-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user}
