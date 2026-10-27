"""The droid's distance sensors and lidar, shared by the TF publisher, the lidar launch,
the web console's sensor setup and (later) the Pico bridge and the safety stop.

sensors.yaml has one block per sensor, keyed by its name:

    tof_front_left:            # name: lower case, digits, _ ; frame tof_front_left_link
      type: vl53l0x            # vl53l0x | hcsr04 | rplidar_c1 (at most one lidar)
      x: 0.225                 # metres from the floor under the body centre (base_link):
      y: 0.07                  #   x forward, y left, z up (ROS REP 103)
      z: 0.25
      yaw_deg: 30              # where it points: + = left
      pitch_deg: 0             # + = down (a sensor looking at the floor for steps)
      fov_deg: 25              # optional, default by type
      range_max: 1.2           # optional, default by type (range_min too)
      stop_distance: 0.30      # stop the feet when closer than this; 0 = never
      pico: {xshut: 2}         # Pico GPIO: vl53l0x {xshut}, hcsr04 {trig, echo}
    lidar:
      type: rplidar_c1
      port: /dev/r2-lidar
      x: 0.17
      ...
      fov_deg: 200             # what the droid does not hide; the rest is cut from /scan

The web console's sensor setup saves its own sensors.yaml in ~/.config/ros2d2/; when
that file exists it is used instead of the package's one (see config_path).

Careful: cameras.yaml has yaw_deg + = right (from the dome's front); here + = left, as TF.
"""

import math
import os
import re

import yaml

USER_CONFIG = os.path.expanduser("~/.config/ros2d2/sensors.yaml")

TYPES = {
    "rplidar_c1": {"fov_deg": 200.0, "range_min": 0.05, "range_max": 12.0},
    "vl53l0x": {"fov_deg": 25.0, "range_min": 0.03, "range_max": 1.2},
    "hcsr04": {"fov_deg": 30.0, "range_min": 0.02, "range_max": 3.0},
}
LIDARS = ("rplidar_c1",)
PICO_PINS = {"vl53l0x": ("xshut",), "hcsr04": ("trig", "echo")}
NAME = re.compile(r"^[a-z][a-z0-9_]*$")
PORT = re.compile(r"^/dev/[A-Za-z0-9_./-]+$")
GPIO = range(0, 29)
# Not for sensors: the VL53L0X's I2C (GP16 SDA, GP17 SCL) and the board's own (GP25 = LED)
PICO_RESERVED = (16, 17, 23, 24, 25)
PICO_MAX = 12                     # the Pico's firmware refuses more (CFG ERR too many)


class SensorConfigError(ValueError):
    pass


def config_path(default):
    """The sensors.yaml to use: the one saved from the web console, if any, else default."""
    return USER_CONFIG if os.path.isfile(USER_CONFIG) else default


class _Loader(yaml.SafeLoader):
    """SafeLoader that refuses a sensor name written twice (plain YAML keeps the last one)."""


def _mapping(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, (str, int, float, bool)) and key is not None:
            raise SensorConfigError(f"line {key_node.start_mark.line + 1}: a name must be plain text")
        if key in keys:
            raise SensorConfigError(f"{key}: duplicated")
        keys.add(key)
    return loader.construct_mapping(node, deep=deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _number(name, s, key, default=None):
    v = s.get(key, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SensorConfigError(f"{name}: {key} must be a number")
    return float(v)


def _sensor(name, raw):
    if not isinstance(name, str) or not NAME.match(name):
        raise SensorConfigError(f"{name}: name must be lower case letters, digits and _")
    if not isinstance(raw, dict):
        raise SensorConfigError(f"{name}: settings must be a block of key: value")
    kind = raw.get("type")
    if not isinstance(kind, str) or kind not in TYPES:
        raise SensorConfigError(f"{name}: type must be one of {', '.join(TYPES)}")
    s = {**TYPES[kind], "yaw_deg": 0.0, "pitch_deg": 0.0, "stop_distance": 0.0, **raw}
    for key in ("x", "y", "z", "yaw_deg", "pitch_deg", "fov_deg", "range_min", "range_max", "stop_distance"):
        if key not in raw and key in ("x", "y", "z"):
            raise SensorConfigError(f"{name}: {key} is missing")
        s[key] = _number(name, s, key)
    if not 0 < s["fov_deg"] <= 360:
        raise SensorConfigError(f"{name}: fov_deg must be more than 0 and at most 360")
    if not 0 <= s["range_min"] < s["range_max"]:
        raise SensorConfigError(f"{name}: range_max must be more than range_min")
    if not 0 <= s["stop_distance"] < s["range_max"]:
        raise SensorConfigError(f"{name}: stop_distance must be 0 (never) or less than range_max")
    if kind in LIDARS:
        if not isinstance(s.get("port"), str) or not PORT.match(s["port"]):
            raise SensorConfigError(f"{name}: port must be a device path like /dev/r2-lidar")
    else:
        pico = s.get("pico")
        want = PICO_PINS[kind]
        if not isinstance(pico, dict) or set(pico) != set(want):
            raise SensorConfigError(f"{name}: pico must be {{{': N, '.join(want)}: N}}")
        pins = [pico[k] for k in want]
        if any(isinstance(p, bool) or not isinstance(p, int) or p not in GPIO for p in pins):
            raise SensorConfigError(f"{name}: pico pins are GPIO 0 to 28")
        for p in pins:
            if p in PICO_RESERVED:
                raise SensorConfigError(f"{name}: GP{p} is reserved (I2C or the board)")
        if len(set(pins)) != len(pins):
            raise SensorConfigError(f"{name}: pico pins must be different")
    return s


def parse_sensors(text):
    """{name: settings} in file order, with the defaults filled in. Raises SensorConfigError."""
    try:
        cfg = yaml.load(text, Loader=_Loader)
    except yaml.YAMLError as e:
        raise SensorConfigError(f"YAML: {e}") from None
    if cfg is None:
        return {}
    if not isinstance(cfg, dict):
        raise SensorConfigError("sensors.yaml must be a list of sensors (name: settings)")
    out, used = {}, {}
    for name, raw in cfg.items():
        s = _sensor(name, raw)
        for pin in (s.get("pico") or {}).values():
            if pin in used:
                raise SensorConfigError(f"{name}: pico pin {pin} is already used by {used[pin]}")
            used[pin] = name
        out[name] = s
    if sum(s["type"] in PICO_PINS for s in out.values()) > PICO_MAX:
        raise SensorConfigError(f"at most {PICO_MAX} sensors on the Pico")
    if sum(s["type"] in LIDARS for s in out.values()) > 1:
        raise SensorConfigError("only one lidar is supported")
    return out


def load_sensors(path):
    with open(path, encoding="utf-8") as f:
        return parse_sensors(f.read())


class Reloader:
    """Re-reads sensors.yaml when it changes (saved from the web console), so the poses
    follow without a restart. A broken file keeps the last good sensors."""

    def __init__(self, path_fn):
        self.path_fn = path_fn      # () -> path in use (the user's file appears on first save)
        self.sensors = {}
        self.error = None
        self._seen = None

    def poll(self):
        """The new sensors if the file changed and is valid, else None."""
        path = self.path_fn()
        try:
            stamp = (path, os.path.getmtime(path))
        except OSError as e:
            self.error = f"{path}: {e.strerror}"
            return None
        if stamp == self._seen:
            return None
        self._seen = stamp
        try:
            self.sensors = load_sensors(path)
        except Exception as e:     # a hand-edited file must never stop the node  # noqa: BLE001
            self.error = str(e)
            return None
        self.error = None
        return self.sensors


def _quaternion(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy)


def transforms(sensors):
    """[(child frame, (x, y, z), (qx, qy, qz, qw))] from base_link, one per sensor."""
    return [(f"{name}_link", (s["x"], s["y"], s["z"]),
             _quaternion(0.0, math.radians(s["pitch_deg"]), math.radians(s["yaw_deg"])))
            for name, s in sensors.items()]


def lidar_name(sensors):
    return next((n for n, s in sensors.items() if s["type"] in LIDARS), None)


def angle_bounds(sensor):
    """(lower, upper) radians in the lidar's frame: what the droid does not hide."""
    half = math.radians(sensor["fov_deg"] / 2)
    return (-half, half)
