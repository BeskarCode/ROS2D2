"""/api/nav for the Navigation page: read and save nav.yaml. No ROS here, so it can be tested
on its own. The page also sets the navigator's parameters live; Save keeps them."""

import os
import tempfile

from r2_nav.nav_core import NavConfigError, parse_nav


def nav_payload(default, user):
    """What the Navigation page loads. A broken file comes back as `error`, never raises."""
    path = user if os.path.isfile(user) else default
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return {"file": path, "saved": path == user, "yaml": "", "nav": {}, "error": f"{path}: {e.strerror}"}
    try:
        nav, error = parse_nav(text), None
    except NavConfigError as e:
        nav, error = {}, str(e)
    return {"file": path, "saved": path == user, "yaml": text, "nav": nav, "error": error}


def save_nav(text, user):
    """(HTTP code, body). Only a valid file is written, in one go (never half a file)."""
    if not isinstance(text, str):
        return 400, {"error": "not saved: the body must carry the file as text"}
    try:
        parse_nav(text)
    except NavConfigError as e:
        return 400, {"error": f"not saved: {e}"}
    folder = os.path.dirname(user)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".nav-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user}
