# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""/api/sensors for the web console's sensor setup: read and save sensors.yaml.
No ROS here, so it can be tested on its own."""

import os

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
    with open(user, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    return 200, {"ok": True, "file": user}
