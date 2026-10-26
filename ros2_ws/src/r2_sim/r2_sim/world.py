"""The simulated room, without ROS: walls, obstacles with a height, R2's pose, and pretend
sensors that see it the way the real ones would (a beam passes over anything lower than
itself; ultrasonics get ghost echoes and lost echoes; everything jitters a little).

Frame: odom, metres, x right/forward of the room, y left; th in radians.
"""

import copy
import json
import math
import random
import re

FOOTPRINT = 0.30          # m: R2's body and feet, as a circle, for bumping into things
ROOM = (-3.0, 3.0, -2.0, 2.0)
KINDS = {                 # defaults for each kind of obstacle
    "post": {"r": 0.025, "height": 0.75},     # a chair leg (r 0.15, 1.7 m: a person)
    "box": {"w": 0.5, "h": 0.5, "height": 0.6},
    "low": {"w": 0.3, "h": 0.3, "height": 0.10},   # under the lidar
}
FOOT = re.compile(r"^ROS:FOOT:(-?\d+),(-?\d+)$")


def _walls(room):
    x0, x1, y0, y1 = room
    return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]


def _box_segs(o):
    x0, x1, y0, y1 = o["x"] - o["w"] / 2, o["x"] + o["w"] / 2, o["y"] - o["h"] / 2, o["y"] + o["h"] / 2
    return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]


def _ray_seg(ox, oy, dx, dy, seg):
    x1, y1, x2, y2 = seg
    ex, ey = x2 - x1, y2 - y1
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return math.inf
    t = ((x1 - ox) * ey - (y1 - oy) * ex) / den
    u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
    return t if t > 0 and 0 <= u <= 1 else math.inf


def _ray_circle(ox, oy, dx, dy, o):
    fx, fy = o["x"] - ox, o["y"] - oy
    along = fx * dx + fy * dy
    off2 = fx * fx + fy * fy - along * along
    r = o["r"]
    return along - math.sqrt(r * r - off2) if along > 0 and off2 <= r * r else math.inf


class World:
    def __init__(self, obstacles=(), pose=(0.0, 0.0, 0.0), room=ROOM):
        self.room = tuple(room)
        self.obstacles = [dict(o) for o in obstacles]
        self.pose = list(pose)
        self.noise = True
        self.next_id = max((o["id"] for o in self.obstacles), default=0) + 1
        self._initial = (copy.deepcopy(self.obstacles), list(self.pose))

    @classmethod
    def empty(cls):
        w = cls()
        w.noise = False
        return w

    @classmethod
    def default(cls):
        obs = [
            {"id": 1, "kind": "box", "x": 0.2, "y": 0.0, "w": 0.8, "h": 0.5, "height": 0.75},
            {"id": 2, "kind": "post", "x": -0.9, "y": 0.5, "r": 0.025, "height": 0.75},
            {"id": 3, "kind": "post", "x": -0.6, "y": 0.5, "r": 0.025, "height": 0.75},
            {"id": 4, "kind": "post", "x": 1.3, "y": -0.9, "r": 0.15, "height": 1.7},
            {"id": 5, "kind": "low", "x": 1.0, "y": 1.1, "w": 0.35, "h": 0.35, "height": 0.10},
        ]
        return cls(obs, (-2.2, -1.2, math.radians(20)))

    def to_json(self):
        return json.dumps({"room": list(self.room), "obstacles": self.obstacles, "pose": self.pose, "noise": self.noise})

    @classmethod
    def from_json(cls, text):
        d = json.loads(text)
        w = cls(d.get("obstacles", []), d.get("pose", (0, 0, 0)), d.get("room", ROOM))
        w.noise = bool(d.get("noise", True))
        return w

    # ---------- editing (from the web page) ----------
    def apply(self, cmd):
        """One edit. Returns None when done, or a sentence saying what is wrong."""
        op = cmd.get("op")
        try:
            if op == "add":
                kind = cmd.get("kind")
                if kind not in KINDS:
                    return f"kind must be one of {', '.join(KINDS)}"
                o = {"id": self.next_id, "kind": kind, "x": float(cmd["x"]), "y": float(cmd["y"])}
                for k, v in KINDS[kind].items():
                    o[k] = float(cmd.get(k, v))
                self.next_id += 1
                self.obstacles.append(o)
                return None
            if op == "move":
                o = self._find(cmd["id"])
                if o is None:
                    return f"no obstacle {cmd['id']}"
                o["x"], o["y"] = float(cmd["x"]), float(cmd["y"])
                return None
            if op == "remove":
                if self._find(cmd["id"]) is None:
                    return f"no obstacle {cmd['id']}"
                self.obstacles = [o for o in self.obstacles if o["id"] != cmd["id"]]
                return None
            if op == "reset":
                self.obstacles, self.pose = copy.deepcopy(self._initial[0]), list(self._initial[1])
                self.next_id = max((o["id"] for o in self.obstacles), default=0) + 1
                return None
            if op == "place":
                self.pose = [float(cmd["x"]), float(cmd["y"]), float(cmd.get("th", 0.0))]
                return None
            if op == "noise":
                self.noise = bool(cmd.get("on"))
                return None
        except (KeyError, TypeError, ValueError) as e:
            return f"{op}: missing or bad value ({e})"
        return "op must be add, move, remove, reset, place or noise"

    def _find(self, oid):
        return next((o for o in self.obstacles if o["id"] == oid), None)

    # ---------- what a beam hits ----------
    def cast(self, x, y, angle, max_d, z_at):
        """Distance along a ray, or None beyond max_d. z_at(d): the beam's lowest height at
        distance d; anything lower than that is missed (walls are always hit)."""
        dx, dy = math.cos(angle), math.sin(angle)
        best = min(_ray_seg(x, y, dx, dy, s) for s in _walls(self.room))
        for o in self.obstacles:
            if o["kind"] == "post":
                d = _ray_circle(x, y, dx, dy, o)
            else:
                d = min(_ray_seg(x, y, dx, dy, s) for s in _box_segs(o))
            if d < best and z_at(d) <= o["height"]:
                best = d
        return best if best <= max_d else None


def sensor_pose(pose, s):
    """Where a sensor of sensors.yaml is in the room, and where it points."""
    x, y, th = pose
    return (x + s["x"] * math.cos(th) - s["y"] * math.sin(th),
            y + s["x"] * math.sin(th) + s["y"] * math.cos(th),
            th + math.radians(s["yaw_deg"]))


class SensorSim:
    """Pretend lidar and distance sensors. The same seed gives the same readings."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def scan(self, world, pose, lidar, step_deg=0.5):
        """A full turn from -pi in the lidar's frame: (angle_min, increment, ranges with inf)."""
        x, y, a0 = sensor_pose(pose, lidar)
        inc = math.radians(step_deg)
        n = int(round(2 * math.pi / inc))
        out = []
        for i in range(n):
            a = -math.pi + i * inc
            d = world.cast(x, y, a0 + a, lidar["range_max"], lambda _d: lidar["z"])
            if d is not None and world.noise:
                d = max(lidar["range_min"], d + self.rng.gauss(0, 0.01))
            out.append(math.inf if d is None else d)
        return -math.pi, inc, out

    def range_of(self, world, pose, s):
        """What a VL53L0X or HC-SR04 reads: the nearest of 5 rays across its cone, or None."""
        if s.get("pitch_deg", 0) > 30:                       # looking at the floor
            d = s["z"] / math.sin(math.radians(s["pitch_deg"]))
            return d + (self.rng.gauss(0, 0.015) if world.noise else 0.0)
        x, y, a0 = sensor_pose(pose, s)
        half = math.radians(s["fov_deg"] / 2)
        low = lambda d: s["z"] - d * math.tan(half)          # noqa: E731  lowest edge of the cone
        hits = [world.cast(x, y, a0 + k * half / 2, s["range_max"], low) for k in (-2, -1, 0, 1, 2)]
        hits = [h for h in hits if h is not None]
        d = min(hits) if hits else None
        if not world.noise:
            return d
        r = self.rng.random()
        if s["type"] == "hcsr04":
            if r < 0.03:
                return None                                   # echo lost
            if r < 0.06:
                return self.rng.uniform(0.2, 1.5)             # ghost: another sonar's ping
            return None if d is None else max(s["range_min"], d + self.rng.gauss(0, 0.02 + 0.01 * d))
        if d is None:
            return self.rng.uniform(0.05, 0.45) if r < 0.01 else None
        return max(s["range_min"], d + self.rng.gauss(0, 0.015))


def parse_foot(line):
    """(drive, turn) from a ROS:FOOT: line that really went to the Mega, else None."""
    m = FOOT.match(line.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def step_pose(pose, v, w, dt):
    x, y, th = pose
    mid = th + w * dt / 2
    return (x + v * dt * math.cos(mid), y + v * dt * math.sin(mid), th + w * dt)


def blocked_move(world, pose):
    """True if R2 standing at pose would overlap a wall or an obstacle."""
    x, y, _ = pose
    x0, x1, y0, y1 = world.room
    if not (x0 + FOOTPRINT <= x <= x1 - FOOTPRINT and y0 + FOOTPRINT <= y <= y1 - FOOTPRINT):
        return True
    for o in world.obstacles:
        if o["kind"] == "post":
            if math.hypot(x - o["x"], y - o["y"]) < o["r"] + FOOTPRINT:
                return True
        else:
            # distance to the box itself (round corners), not to a box grown into a bigger square
            dx = max(abs(x - o["x"]) - o["w"] / 2, 0.0)
            dy = max(abs(y - o["y"]) - o["h"] / 2, 0.0)
            if math.hypot(dx, dy) < FOOTPRINT:
                return True
    return False
