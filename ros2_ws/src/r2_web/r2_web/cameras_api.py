# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Saving cameras.yaml from the console (POST /api/cameras)."""

import os

import yaml

from r2_camera.config import load_cameras


def save_cameras(body, user):
    """(HTTP code, body). body: the request's JSON ({"yaml": text}). Written whole or not at all
    (a temporary file in the same folder, checked, then put in place): a battery cut half way
    through must not leave a truncated cameras.yaml that every camera page then fails on."""
    try:
        text = body["yaml"]
        if not isinstance(text, str):
            raise ValueError("yaml must be text")
        parsed = yaml.safe_load(text) or {}
        if not isinstance(parsed, dict):
            raise ValueError("cameras.yaml must be a list of cameras (name: settings) or auto:")
    except (ValueError, KeyError, TypeError, yaml.YAMLError) as e:
        return 400, {"error": f"not saved: {e}"}
    os.makedirs(os.path.dirname(user), exist_ok=True)
    tmp = f"{user}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    try:
        load_cameras(tmp, found=[])          # read back the way the nodes will read it
    except (ValueError, TypeError, AttributeError, yaml.YAMLError) as e:
        os.remove(tmp)
        return 400, {"error": f"not saved: {e}"}
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user}
