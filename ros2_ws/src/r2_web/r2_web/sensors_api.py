# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/sensors for the web console's sensor setup: read and save sensors.yaml.
No ROS here, so it can be tested on its own."""

import os
import re

from r2_sensors.config import SensorConfigError, parse_sensors


def sensors_payload(default, user, lidar_dev="/dev/r2-lidar"):
    """What the sensor setup page loads. A broken file comes back as `error`, never raises."""
    path = user if os.path.isfile(user) else default
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return {"file": path, "saved": path == user, "yaml": "", "sensors": {},
                "error": f"{path}: {e.strerror}", "lidar_device": os.path.exists(lidar_dev)}
    try:
        sensors, error = parse_sensors(text), None
    except SensorConfigError as e:
        sensors, error = {}, str(e)
    return {"file": path, "saved": path == user, "yaml": text, "sensors": sensors,
            "error": error, "lidar_device": os.path.exists(lidar_dev)}


def save_sensors(text, user):
    """(HTTP code, body). Only a valid file is written; a bad one leaves the old file alone."""
    try:
        parse_sensors(text)
    except SensorConfigError as e:
        return 400, {"error": f"not saved: {e}"}
    os.makedirs(os.path.dirname(user), exist_ok=True)
    text = text if text.endswith("\n") else text + "\n"
    tmp = f"{user}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:     # whole file or nothing: the nodes re-read it any time
        f.write(text)
    os.replace(tmp, user)
    return 200, {"ok": True, "file": user, "yaml": text}


def set_enabled(default, user, name, enabled):
    """(HTTP code, body). The console's in use / ignored switch: changes only that sensor's
    enabled line in the saved sensors.yaml (the package's when none was saved yet), so nothing
    else - comments, or changes not saved in the console - is touched."""
    path = user if os.path.exists(user) else default
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        sensors = parse_sensors(text)
    except (OSError, SensorConfigError) as e:
        return 400, {"error": f"not saved: {e}"}
    if name not in sensors:
        return 400, {"error": f"not saved: unknown sensor {name} in {path} (save the console first)"}
    lines = text.splitlines(keepends=True)
    head = re.compile(rf"^{re.escape(name)}:\s*(#.*)?$")
    start = next((i for i, ln in enumerate(lines) if head.match(ln.rstrip("\r\n"))), None)
    if start is None:
        return 400, {"error": f"not changed: {name} is not written as a block in {path}; set its enabled line in the File tab"}
    end = next((i for i in range(start + 1, len(lines)) if lines[i][:1] not in (" ", "\t", "\n", "\r", "#")), len(lines))
    value = f"  enabled: {'true' if enabled else 'false'}\n"
    at = next((i for i in range(start + 1, end) if lines[i].lstrip().startswith("enabled:")), None)
    if at is not None:
        lines[at] = value
    else:
        after = next((i for i in range(start + 1, end) if lines[i].lstrip().startswith("type:")), start)
        lines.insert(after + 1, value)
    return save_sensors("".join(lines), user)
