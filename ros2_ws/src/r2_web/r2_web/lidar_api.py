# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Saving sensors.yaml from the console: does the lidar's driver need a restart?

Only the scan mode and upside-down mounting are the driver's own parameters (the rest: scan_crop
and lidar_motor follow the file by themselves), so only they restart r2d2-lidar.
"""

from r2_sensors.config import SensorConfigError, lidar_name, parse_sensors


def _driver(text):
    sensors = parse_sensors(text)
    name = lidar_name(sensors)
    return None if name is None else (sensors[name]["scan_mode"], sensors[name]["inverted"])


def lidar_needs_restart(old_text, new_text):
    try:
        return _driver(old_text) != _driver(new_text)
    except SensorConfigError:
        return False
