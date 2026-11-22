# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""From the BNO085's axes to R2's, and the settings the console writes (pure: no ROS).

The board sits in the box, and the box sits in R2 about 10 degrees off level; with the box lying the
board on the divider is upside down (roll near 180). "Level here" stores the chip's whole roll and pitch
with R2 still on a flat floor, so the correction undoes the box's tilt and the flip alike. Then `front`
turns round R2's vertical: which of the board's arrows points to R2's front.

Rotations: the chip's attitude is Rz(yaw)·Ry(pitch)·Rx(roll) (the ROS order rvc.quaternion uses).
The mount M = Rz(-θ)·L, L = Ry(level pitch)·Rx(level roll), θ = where L puts the front arrow, takes a vector in the chip's axes to R2's;
R2's attitude is the chip's times Mᵀ.
"""

import math
import os
import tempfile

import yaml

G = 9.80665
DEFAULTS = {"in_use": True, "port": "/dev/ttyAMA3", "box": "standing", "front": "+x",
            "invert_yaw": False, "level": None}
FRONT_ARROW = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0)}
BOXES = ("standing", "lying")
LEVEL_MIN_SAMPLES = 50          # half a second at 100 frames a second
LEVEL_STILL_DEG = 1.0           # every frame of the last second this close to the mean


def _rx(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rz(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _t(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _euler(r):
    """(yaw, pitch, roll) in degrees from a rotation matrix, ZYX."""
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -r[2][0]))))
    return (math.degrees(math.atan2(r[1][0], r[0][0])), pitch, math.degrees(math.atan2(r[2][1], r[2][2])))


class Mount:
    """How the board sits in R2: `level` ({roll_deg, pitch_deg} or None) and `front` ("+x" ...)."""

    def __init__(self, level, front):
        lv = _mul(_ry(level["pitch_deg"]), _rx(level["roll_deg"])) if level else _rz(0.0)
        # the printed arrow, once levelled, lies flat: turn round R2's vertical until it points forward.
        # (Worked out from the arrow, not a fixed angle: on the upside-down board of the lying box +Y and -Y
        # swap sides, and a fixed table would put R2's front behind it.)
        a = _apply(lv, FRONT_ARROW[front])
        m = _mul(_rz(-math.degrees(math.atan2(a[1], a[0]))), lv)
        self.m = m
        self.mt = _t(m)

    def to_r2(self, yaw, pitch, roll):
        """The chip's yaw, pitch, roll (degrees) as R2's."""
        chip = _mul(_rz(yaw), _mul(_ry(pitch), _rx(roll)))
        return _euler(_mul(chip, self.mt))

    def vec(self, v):
        """A vector in the chip's axes (acceleration, turn rate) in R2's."""
        return _apply(self.m, v)


def linear_accel(pitch, roll, a):
    """Acceleration in R2's axes without gravity (what moves R2), m/s²."""
    g = _apply(_t(_mul(_ry(pitch), _rx(roll))), (0.0, 0.0, G))
    return tuple(a[i] - g[i] for i in range(3))


def _wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def _circular_mean(xs):
    return math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in xs),
                                   sum(math.cos(math.radians(x)) for x in xs)))


def level_from(samples):
    """The chip's (roll, pitch) of the last second → ({"roll_deg", "pitch_deg"}, "") or (None, why)."""
    if len(samples) < LEVEL_MIN_SAMPLES:
        return None, "no frames from the IMU (is it connected?)"
    roll = _circular_mean([s[0] for s in samples])
    pitch = _circular_mean([s[1] for s in samples])
    spread = max(max(abs(_wrap(s[0] - roll)), abs(_wrap(s[1] - pitch))) for s in samples)
    if spread > LEVEL_STILL_DEG:
        return None, f"keep R2 still on a flat floor (it moved {spread:.1f}° in the last second)"
    return {"roll_deg": round(roll, 2), "pitch_deg": round(pitch, 2)}, ""


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_setting(name, value):
    """"" if `value` is good for `name`, else why not."""
    if name in ("in_use", "invert_yaw"):
        return "" if isinstance(value, bool) else f"{name} must be true or false"
    if name == "port":
        return "" if isinstance(value, str) and value.strip() else "port must be a device, e.g. /dev/ttyAMA3"
    if name == "box":
        return "" if value in BOXES else f"box must be one of {', '.join(BOXES)}"
    if name == "front":
        return "" if value in FRONT_ARROW else f"front must be one of {', '.join(FRONT_ARROW)}"
    if name == "level":
        if value is None:
            return ""
        if isinstance(value, dict) and _number(value.get("roll_deg")) and _number(value.get("pitch_deg")):
            return ""
        return "level must be empty or {roll_deg, pitch_deg}"
    return f"unknown setting {name}"


def load_user(path):
    """The user's settings over DEFAULTS, and what was wrong with the file ("" if nothing)."""
    cfg = dict(DEFAULTS)
    if not os.path.exists(path):
        return cfg, ""
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:   # a file saved by an ANSI editor too
        return cfg, f"{path}: cannot read it ({str(e).splitlines()[0]}); using the defaults"
    if data is None:
        return cfg, ""
    if not isinstance(data, dict):
        return cfg, f"{path}: not a list of settings; using the defaults"
    errors = []
    for k in DEFAULTS:
        if k in data:
            why = check_setting(k, data[k])
            if why:
                errors.append(why)
            else:
                cfg[k] = data[k]
    return cfg, "; ".join(errors)


def save_user(path, cfg):
    """Write the settings (only the known ones), all at once: a cut never leaves half a file."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    out = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".imu-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# The BNO085 IMU's settings, written by the console (Setup → IMU) and the IMU node.\n")
        yaml.safe_dump(out, f, sort_keys=False)
    os.replace(tmp, path)
