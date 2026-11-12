# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The navigator's logic, without ROS: go to a goal, steer round what the sensors see, stop at
the safety circle, and when blocked run a short sequence (wait, back up, turn); give up after
a few tries and stay stopped. The same code runs on the droid and in the simulator.

Frames: the pose is in odom (x, y, th); obstacle points are in base_link (x forward, y left);
headings are relative to the droid (0 = ahead, + = left). Sensors come from sensors.yaml.

nav.yaml (the web console's Navigation page edits it):

    safety_radius: 0.55       # m from the body centre: the droid keeps everything outside it
    slow_from: 0.80           # m beyond the circle where it starts slowing down
    max_speed: 0.35           # m/s (the Mega bridge caps at 0.4)
    max_turn_deg: 15          # deg/s (the bridge caps at 0.6 rad/s = 34)
    accel: 0.25               # m/s²: ramps applied by the node to what goes to the feet (40 kg)
    turn_accel_deg: 20        # deg/s²: the same for turning
    max_drive_power: 40       # Sabertooth units, like ShadowMD's drivespeed: a cap on top of max_speed
    max_turn_power: 30        # Sabertooth units, like ShadowMD's turnspeed
    goal_tolerance: 0.25      # m
    sensors_may_stop_earlier: true   # a sensor's own stop_distance wins when larger
    filter: true              # median of 5 + smoothing on the distance sensors
    on_blocked: turn          # turn | reverse | wait
    allow_reverse: true
    give_up_after: 3          # tries; then it stops until it gets a new goal
    sounds: {auto_on: "S1:$11", obstacle: "S1:$21", blocked: "S1:$31", give_up: "S1:$41", arrived: "S1:$W"}
"""

import copy
import json
import math
import os
import re
from dataclasses import dataclass, field

import yaml

USER_CONFIG = os.path.expanduser("~/.config/ros2d2/nav.yaml")
EVENTS = ("auto_on", "obstacle", "blocked", "give_up", "arrived")
DEFAULTS = {
    "safety_radius": 0.55, "slow_from": 0.80, "max_speed": 0.35, "max_turn_deg": 15, "accel": 0.25,
    "turn_accel_deg": 20, "max_drive_power": 40, "max_turn_power": 30,
    "goal_tolerance": 0.25, "sensors_may_stop_earlier": True, "filter": True, "on_blocked": "turn",
    "allow_reverse": True, "give_up_after": 3,
    "sounds": {"auto_on": "S1:$11", "obstacle": "S1:$21", "blocked": "S1:$31", "give_up": "S1:$41", "arrived": "S1:$W"},
}
RANGES = {"safety_radius": (0.25, 1.5), "slow_from": (0.1, 3.0), "max_speed": (0.05, 0.4), "max_turn_deg": (5, 34),
          "accel": (0.05, 2.0), "turn_accel_deg": (5, 180), "max_drive_power": (5, 127), "max_turn_power": (5, 127),
          "goal_tolerance": (0.05, 1.0), "give_up_after": (1, 20)}
BLOCKED_MODES = ("turn", "reverse", "wait")
SOUND = re.compile(r"^(S1|S3|MD):[ -~]{1,20}$")

REVERSE_SPEED = 0.15     # m/s
REVERSE_MAX = 0.30       # m
WAIT_MAX = 4.0           # s
OBSTACLE_QUIET = 3.0     # s between two "obstacle" sounds
STUCK_AFTER = 12.0       # s without getting 0.15 m closer counts as a try
FREE_STEPS = 8           # steps with the front clear before heading for the goal again
PROGRESS_RESETS = 0.5    # m closer to the goal since the last failed try: the count starts again
DRIFT_AWAY = 0.5         # m further from the goal than the closest it got: counts as a try
DRIVE_UNITS_PER_MPS = 50   # the Mega bridge's conversion (r2_shadow_bridge): units = m/s * 50
TURN_UNITS_PER_RADPS = 30  # and rad/s * 30
SIDE_SLOW_MIN = 0.3        # things beside the path slow R2 down to this fraction at most
FLOOR_NEAR = 0.8         # floor sensor reading below 80% of the floor: something low in the way
FLOOR_FAR = 1.4          # above 140% of the floor (or no echo): a step down or a hole


class NavConfigError(ValueError):
    pass


def config_path(default):
    return USER_CONFIG if os.path.isfile(USER_CONFIG) else default


def parse_nav(text):
    """nav.yaml -> settings with the defaults filled in. Raises NavConfigError naming the key."""
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise NavConfigError(f"YAML: {e}") from None
    if not isinstance(raw, dict):
        raise NavConfigError("nav.yaml must be a list of key: value")
    cfg = copy.deepcopy(DEFAULTS)
    for k, v in raw.items():
        if k not in DEFAULTS:
            raise NavConfigError(f"{k}: unknown setting")
        if k == "sounds":
            if not isinstance(v, dict):
                raise NavConfigError("sounds: must be a block of event: command")
            for ev, cmd in v.items():
                if ev not in EVENTS:
                    raise NavConfigError(f"sounds.{ev}: unknown event")
                if cmd in (None, ""):
                    cmd = ""
                elif not isinstance(cmd, str) or not SOUND.match(cmd):
                    raise NavConfigError(f"sounds.{ev}: must be empty or a command like S1:$11")
                cfg["sounds"][ev] = cmd
            continue
        cfg[k] = v
    for k, (lo, hi) in RANGES.items():
        v = cfg[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise NavConfigError(f"{k}: must be a number from {lo} to {hi}")
    for k in ("sensors_may_stop_earlier", "filter", "allow_reverse"):
        if not isinstance(cfg[k], bool):
            raise NavConfigError(f"{k}: must be true or false")
    if cfg["on_blocked"] not in BLOCKED_MODES:
        raise NavConfigError(f"on_blocked: must be one of {', '.join(BLOCKED_MODES)}")
    cfg["give_up_after"] = int(cfg["give_up_after"])
    return cfg


def load_nav(path):
    with open(path, encoding="utf-8") as f:
        return parse_nav(f.read())


def clamp_param(name, value):
    """A setting changed live, kept inside its range (the page and ros2 param set use this)."""
    if name in RANGES:
        lo, hi = RANGES[name]
        v = min(max(float(value), lo), hi)
        return int(round(v)) if name == "give_up_after" else v
    return value


def ramp(current, wanted, max_step):
    """One step towards `wanted`, no bigger than max_step: no jumps for the feet."""
    return current + max(-max_step, min(max_step, wanted - current))


def state_json(d, goal, heading_odom, filtered, raw, ignored=()):
    """What /nav/state carries for the web page (one JSON object)."""
    r = lambda v: None if v is None else round(v, 3)   # noqa: E731
    return json.dumps({
        "state": d.state, "why": d.why, "v": round(d.v, 3), "w": round(d.w, 3),
        "heading": r(heading_odom), "tries": d.tries, "goal": list(goal) if goal else None,
        "stops": {k: r(v) for k, v in d.stops.items()},
        "filtered": {k: r(v) for k, v in filtered.items()}, "raw": {k: r(v) for k, v in raw.items()},
        "ignored": list(ignored),
    })


# ---------- geometry ----------

def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def is_floor(s):
    return s.get("pitch_deg", 0) > 30


def floor_distance(s):
    """What a sensor looking down at the floor reads on a flat floor."""
    return s["z"] / math.sin(math.radians(s["pitch_deg"]))


def floor_problem(s, d):
    """'something low' / 'no floor' / None for a floor sensor's reading (None = no echo)."""
    e = floor_distance(s)
    if d is None or d > e * FLOOR_FAR:
        return "no floor"
    return "something low" if d < e * FLOOR_NEAR else None


def is_lidar(s):
    return s["type"] == "rplidar_c1"


def to_circle(s, radius):
    """Distance from the sensor to the safety circle along its beam (0 if it is outside)."""
    ux, uy = math.cos(math.radians(s["yaw_deg"])), math.sin(math.radians(s["yaw_deg"]))
    pu = s["x"] * ux + s["y"] * uy
    pp = s["x"] ** 2 + s["y"] ** 2
    return max(0.0, -pu + math.sqrt(max(0.0, pu * pu - (pp - radius * radius))))


def braking(speed, cfg):
    """Metres it takes to stop from `speed` with the configured deceleration."""
    return speed * speed / (2 * cfg["accel"])


def nearest_ahead(points):
    """Distance from the body centre to the nearest thing in the front half (3.0 if none)."""
    return min((math.hypot(x, y) for x, y in points if x > 0), default=3.0)


def stop_distances(sensors, cfg):
    """{name: metres}: where each sensor stops the droid. 0 = never (lidar). A floor sensor stops
    it when it reads less than this (something low) or much more (no floor)."""
    out = {}
    for name, s in sensors.items():
        if is_lidar(s):
            out[name] = 0.0
            continue
        if is_floor(s):
            out[name] = floor_distance(s) * FLOOR_NEAR
            continue
        d = to_circle(s, cfg["safety_radius"])
        if cfg["sensors_may_stop_earlier"]:
            d = max(d, s.get("stop_distance", 0.0))
        out[name] = d
    return out


class RangeFilter:
    """Median of the last n readings (one ghost echo or one lost echo changes nothing), then
    exponential smoothing. None (nothing seen) when fewer than 3 of the last n saw something."""

    def __init__(self, n=5, alpha=0.5):
        self.n, self.alpha, self.hist, self.value = n, alpha, [], None

    def update(self, reading):
        self.hist = (self.hist + [reading])[-self.n:]
        vals = sorted(v for v in self.hist if v is not None)
        if len(vals) < 3:
            self.value = None
            return None
        med = vals[len(vals) // 2]
        self.value = med if self.value is None else self.value + self.alpha * (med - self.value)
        return self.value


def points_from(scan_xy, ranges, sensors):
    """Obstacle points in base_link: the lidar's, plus one per distance sensor that sees something."""
    pts = list(scan_xy or [])
    for name, d in ranges.items():
        s = sensors.get(name)
        if s is None or d is None or is_lidar(s):
            continue
        if is_floor(s):
            if floor_problem(s, d) == "something low":      # where the beam hit it, on the ground
                h = d * math.cos(math.radians(s["pitch_deg"]))
                a = math.radians(s["yaw_deg"])
                pts.append((s["x"] + h * math.cos(a), s["y"] + h * math.sin(a)))
            continue
        a = math.radians(s["yaw_deg"])
        pts.append((s["x"] + d * math.cos(a), s["y"] + d * math.sin(a)))
    return pts


def clearance(points, heading, half_width=0.36):
    """Free distance from the body centre along a heading, for a body ~0.7 m wide."""
    c, s = math.cos(heading), math.sin(heading)
    best = 3.0
    for x, y in points:
        along, side = x * c + y * s, abs(-x * s + y * c)
        if along > 0 and side < half_width:
            best = min(best, along)
    return best


def choose_heading(points, goal_bearing, cfg):
    """The heading (-90..+90 deg, 10 deg steps) that best mixes 'towards the goal' and 'free'."""
    margin = cfg["safety_radius"] + cfg["slow_from"]
    best = None
    for o in range(-90, 91, 10):
        h = math.radians(o)
        c = clearance(points, h)
        cost = abs(wrap(h - goal_bearing)) / math.pi + (max(0.0, margin - c) * 2.5) + abs(o) / 900
        if best is None or cost < best[2]:
            best = (h, c, cost)
    return best[0], best[1]


# ---------- the navigator ----------

@dataclass
class Decision:
    v: float = 0.0
    w: float = 0.0
    state: str = "idle"
    why: str = ""
    heading: float | None = None      # relative to the droid
    tries: int = 0
    events: list = field(default_factory=list)
    stops: dict = field(default_factory=dict)


class Navigator:
    def __init__(self, cfg, sensors):
        self.cfg, self.sensors = cfg, sensors
        self.goal = None
        self.gave_up = None            # the reason, while stopped after giving up
        self.prev_auto = False
        self._reset_try_state()
        self.tries = 0
        self.last_t = None
        self.last_obstacle = -1e9
        self.floor_seen = set()        # floor sensors that have given a reading since start-up

    def _reset_try_state(self):
        self.phase = None
        self.turn_dir = 0
        self.free_steps = 0
        self.backed = 0.0
        self.waited = 0.0
        self.was_blocked = False
        self.best_d = math.inf
        self.best_t = None
        self.try_d = math.inf          # the closest it had been to the goal at the last failed try
        self.closest = math.inf        # the closest it has been to the goal

    def set_goal(self, x, y):
        self.goal = (x, y)
        self.gave_up = None
        self.tries = 0
        self._reset_try_state()

    def cancel(self):
        self.goal = None
        self._reset_try_state()

    def reconfigure(self, cfg=None, sensors=None):
        self.cfg = cfg or self.cfg
        self.sensors = self.sensors if sensors is None else sensors   # {} = every sensor ignored

    def _front(self):
        return [n for n, s in self.sensors.items() if not is_lidar(s) and not is_floor(s) and abs(s["yaw_deg"]) < 90]

    def _rear(self):
        return next((n for n, s in self.sensors.items() if not is_lidar(s) and not is_floor(s) and abs(s["yaw_deg"]) > 150), None)

    def step(self, now, pose, scan_xy, ranges, auto_on, speed=0.0):
        """One decision. scan_xy: lidar points in base_link, or None when the lidar is silent.
        ranges: {name: metres | None (sees nothing)} for the sensors that are reporting; a
        sensor that stopped reporting is missing from the dict. speed: what the feet are doing
        now (m/s): the front sensors stop it earlier by the distance it needs to brake."""
        dt = 0.1 if self.last_t is None else max(0.0, min(0.5, now - self.last_t))
        self.last_t = now
        cfg = self.cfg
        stops = stop_distances(self.sensors, cfg)
        brake = braking(max(0.0, speed), cfg)
        for n in self._front():
            if stops.get(n):
                stops[n] += brake
        d = Decision(tries=self.tries, stops=stops)
        if auto_on and not self.prev_auto:
            d.events.append("auto_on")
        self.prev_auto = auto_on
        if not auto_on:
            d.state, d.why = "manual", "autonomous mode off: the controller drives"
            return d
        if self.goal is None:
            d.state = "gave up" if self.gave_up else "idle"
            d.why = self.gave_up or "no goal"
            return d
        front = self._front()
        if scan_xy is None and not any(n in ranges for n in front):
            d.state, d.why = "no data", "no lidar and no front sensor reporting: not moving blind"
            return d

        x, y, th = pose
        gx, gy = self.goal
        gd = math.hypot(gx - x, gy - y)
        if gd < cfg["goal_tolerance"]:
            self.goal, self.tries = None, 0
            self._reset_try_state()
            d.state, d.why, d.tries = "arrived", "goal reached", 0
            d.events.append("arrived")
            return d
        want = wrap(math.atan2(gy - y, gx - x) - th)
        pts = points_from(scan_xy, ranges, self.sensors)
        heading, clear = choose_heading(pts, want, cfg)
        too_close = next((n for n in front if ranges.get(n) is not None and stops[n] > 0 and ranges[n] < stops[n]), None)
        floor_why = None
        if too_close is None:
            for n, s in self.sensors.items():
                if is_floor(s) and ranges.get(n) is not None:
                    self.floor_seen.add(n)
                # no echo before the first reading is the filter starting up, not a drop
                if is_floor(s) and n in self.floor_seen and n in ranges and floor_problem(s, ranges[n]):
                    too_close, floor_why = n, floor_problem(s, ranges[n])
                    break

        near = min((ranges[n] for n in front if ranges.get(n) is not None), default=math.inf)
        if near < cfg["slow_from"] and now - self.last_obstacle >= OBSTACLE_QUIET:
            self.last_obstacle = now
            d.events.append("obstacle")

        R = cfg["safety_radius"]
        wm = min(math.radians(cfg["max_turn_deg"]), cfg["max_turn_power"] / TURN_UNITS_PER_RADPS)
        vmax = min(cfg["max_speed"], cfg["max_drive_power"] / DRIVE_UNITS_PER_MPS)
        w = max(-wm, min(wm, 1.0 * heading))
        # slower the closer things are: fully for what is in the way, partly for what is beside it
        slow = lambda dist: max(0.0, min(1.0, (dist - R) / cfg["slow_from"]))   # noqa: E731
        v = vmax * min(slow(clear), max(SIDE_SLOW_MIN, slow(nearest_ahead(pts)))) * max(0.0, math.cos(heading))
        state = "avoiding" if abs(wrap(heading - want)) > math.radians(12) else "going"
        why = ("steering round an obstacle" if state == "avoiding" else "heading for the goal") + f", {gd:.2f} m to go"
        blocked = too_close is not None or clear < R

        self.closest = min(self.closest, gd)
        # progress watchdog: going round in circles, stuck in a corner or wandering away from the
        # goal while steering round things counts as a try too
        if self.best_t is None or gd < self.best_d - 0.15:
            self.best_d, self.best_t = gd, now
        stuck = now - self.best_t > STUCK_AFTER or gd > self.best_d + DRIFT_AWAY
        if stuck:
            self.best_d, self.best_t = gd, now
        if (blocked and not self.was_blocked) or stuck:
            # brushing past a table blocks it briefly again and again while it gets closer:
            # only count tries that come without real progress since the previous one (closer
            # than it had ever been then: wandering off and coming back is not progress)
            self.tries = 1 if self.try_d - gd >= PROGRESS_RESETS else self.tries + 1
            self.try_d = self.closest
            if self.tries > cfg["give_up_after"]:
                n = cfg["give_up_after"]
                self.gave_up = f"could not get past after {n} {'tries' if n > 1 else 'try'}: stopped until a new goal"
                self.goal = None
                self._reset_try_state()
                d.state, d.why, d.tries = "gave up", self.gave_up, self.tries
                d.events.append("give_up")
                self.tries = 0
                return d
            d.events.append("blocked")
        self.was_blocked = blocked
        d.tries = self.tries

        # when blocked: a sequence that runs to its end before heading for the goal again
        rear = self._rear()
        rear_d = ranges.get(rear) if rear else None
        rear_free = rear is not None and rear in ranges and (rear_d is None or rear_d > max(stops.get(rear, 0), 0.2))
        if blocked and self.phase is None:
            mode = cfg["on_blocked"]
            self.phase = "reverse" if mode == "reverse" and cfg["allow_reverse"] else ("wait" if mode == "wait" else "turn")
        if self.phase == "wait":
            if blocked and self.waited < WAIT_MAX:
                self.waited += dt
                d.state, d.why, d.heading = "waiting", f"blocked: waiting {WAIT_MAX - self.waited:.1f} s for the way to clear", heading
                return d
            self.phase, self.waited = ("turn" if blocked else None), 0.0
        if self.phase == "reverse":
            if self.backed < REVERSE_MAX and rear_free and cfg["allow_reverse"]:
                self.backed += REVERSE_SPEED * dt
                d.v, d.state, d.heading = -REVERSE_SPEED, "reversing", math.pi
                d.why = f"backing up {self.backed * 100:.0f} of {REVERSE_MAX * 100:.0f} cm"
                return d
            self.phase, self.backed, self.free_steps = "turn", 0.0, 0
        if self.phase == "turn":
            if not self.turn_dir:
                self.turn_dir = 1 if clearance(pts, math.radians(60)) >= clearance(pts, math.radians(-60)) else -1
            if blocked or self.free_steps < FREE_STEPS:
                self.free_steps = 0 if blocked else self.free_steps + 1
                side = "left" if self.turn_dir > 0 else "right"
                v = 0.0 if blocked else min(v, vmax * 0.5)
                w = 0.7 * wm * self.turn_dir
                state = "stop" if too_close else "turning"
                if floor_why:
                    why = f"STOP: {too_close}: {floor_why} ahead, turning {side}"
                elif too_close:
                    why = f"STOP: {too_close} reads {ranges[too_close]:.2f} m < {stops[too_close]:.2f} m, turning {side}"
                else:
                    why = f"turning {side} until the way is clear"
            else:
                self.phase, self.turn_dir, self.free_steps = None, 0, 0
        d.v, d.w, d.state, d.why, d.heading = v, w, state, why, heading
        return d
