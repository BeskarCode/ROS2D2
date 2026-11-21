# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/remote: read and save remote.yaml, the settings of the console's virtual Navs (the Remote
window and the phone view): the sticks' limit, guest mode and the phone's favourite actions. No ROS
here; the web server tells the Mega bridge to re-read it (/r2/remote/reload) after a save."""

import os
import tempfile

import yaml

from r2_shadow_bridge.remote_cfg import DEFAULTS, RemoteConfigError, parse_remote

HEADER = ("# ROS2D2 Remote window and phone view (saved from the web console).\n"
          "# stick_limit_pct: 5..100, how far the virtual Navs' sticks go; guest: the phone shows only\n"
          "# the actions; favorites: [{combo, name}], the phone's favourite actions.\n")


def remote_yaml(settings):
    """The settings as the file's text (the defaults, when there is no file yet)."""
    return HEADER + yaml.safe_dump(settings, sort_keys=False, allow_unicode=True, default_flow_style=None)


def remote_payload(user):
    """What Setup and the phone load. A broken file comes back as `error` with the defaults, as the
    Mega bridge uses them; never raises."""
    out = {"file": user, "saved": os.path.isfile(user), "yaml": "", "remote": {**DEFAULTS, "favorites": []},
           "error": None}
    if not out["saved"]:
        out["yaml"] = remote_yaml(out["remote"])
        return out
    try:
        with open(user, encoding="utf-8") as f:
            out["yaml"] = f.read()
        out["remote"] = parse_remote(out["yaml"])
    except OSError as e:
        out["error"] = f"{user}: {e.strerror}"
    except RemoteConfigError as e:
        out["error"] = str(e)
    return out


def save_remote(text, user):
    """(HTTP code, body). Only a valid file is written, in one go (never half a file)."""
    if not isinstance(text, str):
        return 400, {"error": "not saved: the body must carry the file as text"}
    try:
        parse_remote(text)
    except RemoteConfigError as e:
        return 400, {"error": f"not saved: {e}"}
    folder = os.path.dirname(user)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".remote-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user}
