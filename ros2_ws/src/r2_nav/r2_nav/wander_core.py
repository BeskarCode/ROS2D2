# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The head of Patrol and Free roam: where R2 strolls, when it stops to look round, the faces it
looks at with the dome and says hello to. No ROS here (test/test_wander_core.py); the wander node
wires it, and the navigator (its legs) drives the course it gives, with all its safety.

States:
  walk       along the course; every turn_every_s a new one (± turn_deg), sometimes (pause_chance)
             a stop to look round first
  look       feet still for pause_s; the dome follows a face, or sweeps slowly left and right
  greet      a new face close enough (greet_size): feet still, the hello sound once; while it stays,
             at most greet_s; then off the other way. No other hello for greet_cooldown_s
  turn_away  the navigator blocked for blocked_s: a new course 120-180 deg away (one step)

Patrol keeps near where it started: outside `radius`, the new courses point home (± heading_home_deg).
Angles: courses in rad (odom); faces and the dome in degrees, + = right, as r2_dome_tracker.
"""

import math
from dataclasses import dataclass, field

from r2_dome_tracker.control import REF_HALF_FOV, DomeTracker, FaceLock
from r2_nav.modes import WANDER_MODES

BLOCKED = ("searching", "gave up")      # /nav/state states that count as blocked
SWEEP_DEG = 45.0                         # looking round: the dome goes this far each side
FRONT_DEG = 5.0                          # within this of the front the dome counts as facing front
CLEAR_S = 1.0                            # not blocked for this long (in a row) before the blocked count starts again


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


@dataclass
class WanderOut:
    heading: float | None = None          # the course, rad in odom (None: no pose yet)
    hold: bool = False                    # feet still
    dome: int = 0                         # DM: speed
    sounds: list = field(default_factory=list)
    state: str = "walk"
    home_dist: float | None = None        # m from where the mode started (None: no pose)


class Wander:
    def __init__(self, cfg, gains, rng, radius, lock_gate_deg=15.0, lock_calm_s=2.0):
        self.cfg, self.gains, self.rng, self.radius = cfg, gains, rng, radius
        self.lock = FaceLock(lock_gate_deg, lock_calm_s)
        self.tracker = DomeTracker(gains)

    def start(self, now, pose):
        """The mode just switched on: the start (for the radius) is where R2 is now."""
        self.origin = None if pose is None else (pose[0], pose[1])
        self.heading = None if pose is None else pose[2]
        self.state = "walk"
        self.next_turn = now + self.rng.uniform(*self.cfg["turn_every_s"])
        self.until = None                 # end of look or greet
        self.last_greet = -math.inf
        self.blocked_since = None
        self.free_since = None
        self.keep_until = -math.inf       # after a turn away: no "back home now" until then
        self.sweep = 1
        self.lock.reset()
        self.tracker.reset()

    # ---------- the course ----------
    def _home(self, pose):
        """(distance, bearing) to the start, or None."""
        if pose is None or self.origin is None:
            return None
        dx, dy = self.origin[0] - pose[0], self.origin[1] - pose[1]
        return math.hypot(dx, dy), math.atan2(dy, dx)

    def _outside(self, home):
        return self.radius and home is not None and home[0] > self.cfg["radius"]

    def _towards_home(self, home):
        h = math.radians(self.cfg["heading_home_deg"])
        return wrap(home[1] + self.rng.uniform(-h, h))

    def _new_course(self, home):
        if self._outside(home):
            return self._towards_home(home)
        lo, hi = self.cfg["turn_deg"]
        return wrap(self.heading + self.rng.choice((-1, 1)) * math.radians(self.rng.uniform(lo, hi)))

    def _walk(self, now):
        self.state, self.until = "walk", None
        self.next_turn = now + self.rng.uniform(*self.cfg["turn_every_s"])
        self.blocked_since = self.free_since = None   # blocked before a stop (someone in the way) is not blocked now

    # ---------- the dome ----------
    def _dome_towards(self, direction):
        """DM: speed that turns the dome towards + (direction 1) or - (-1), slowly."""
        return int(direction * self.gains.min_speed * (-1 if self.gains.invert else 1))

    def _dome(self, now, face, waiting, dome_deg):
        if face is not None:
            self.tracker.face(face[3] / REF_HALF_FOV, face[0])
            return self.tracker.speed(now)
        self.tracker.no_face()
        if waiting:
            return 0                       # lost it a moment ago: still, it may come back
        if self.state == "look":
            if dome_deg >= SWEEP_DEG:
                self.sweep = -1
            elif dome_deg <= -SWEEP_DEG:
                self.sweep = 1
            return self._dome_towards(self.sweep)
        if abs(dome_deg) < FRONT_DEG:
            return 0
        return self._dome_towards(-1 if dome_deg > 0 else 1)

    # ---------- one step ----------
    def step(self, now, pose, nav_state, faces, dome_deg):
        """faces: [(t, bearing_deg, size)] seen recently, bearing from the dome's front, size a fraction
        of the picture width. dome_deg: the dome's estimated angle."""
        cfg = self.cfg
        out = WanderOut()
        if pose is not None:
            if self.origin is None:
                self.origin = (pose[0], pose[1])
            if self.heading is None:
                self.heading = pose[2]
        home = self._home(pose)

        # faces in a frame that does not turn with the dome (as the dome tracker does)
        best, new, waiting = self.lock.update([(t, b + dome_deg, size, b) for t, b, size in faces], now)

        if self.state == "turn_away":
            self._walk(now)
        if best is not None and new and best[2] >= cfg["greet_size"] and now - self.last_greet >= cfg["greet_cooldown_s"]:
            self.state, self.until, self.last_greet = "greet", now + cfg["greet_s"], now
            self.blocked_since = self.free_since = None
            if cfg["hello"]:
                out.sounds.append(cfg["hello"])
        elif self.state == "greet":
            if (best is None and not waiting) or now >= self.until:
                if self.heading is not None:
                    t0 = math.radians(cfg["turn_deg"][0])
                    self.heading = wrap(self.heading + math.pi + self.rng.uniform(-t0, t0))
                self._walk(now)
        elif self.state == "look":
            if now >= self.until:
                self._walk(now)
        elif self.state == "walk" and pose is not None:
            # blocked: the navigator searching (or given up), even if it flickers back to going for a step
            if nav_state in BLOCKED:
                self.free_since = None
                if self.blocked_since is None:
                    self.blocked_since = now
            elif self.blocked_since is not None:
                self.free_since = now if self.free_since is None else self.free_since
                if now - self.free_since >= CLEAR_S:
                    self.blocked_since = self.free_since = None
            if self.blocked_since is not None and now - self.blocked_since >= cfg["blocked_s"]:
                self.heading = wrap(self.heading + self.rng.choice((-1, 1)) * math.radians(self.rng.uniform(120, 180)))
                self.state, self.blocked_since, self.free_since = "turn_away", None, None
                self.next_turn = now + self.rng.uniform(*cfg["turn_every_s"])
                self.keep_until = self.next_turn       # the way home is blocked: away from it until the next course
            elif self._outside(home) and now >= self.keep_until and abs(wrap(self.heading - home[1])) > math.pi / 2:
                self.heading = self._towards_home(home)       # going further out: back now
                self.next_turn = now + self.rng.uniform(*cfg["turn_every_s"])
            elif now >= self.next_turn:
                self.heading = self._new_course(home)
                self.next_turn = now + self.rng.uniform(*cfg["turn_every_s"])
                if self.rng.random() < cfg["pause_chance"]:
                    self.state, self.until = "look", now + self.rng.uniform(*cfg["pause_s"])
                    self.blocked_since = self.free_since = None
                    if cfg["idle_sounds"] and self.rng.random() < cfg["pause_chance"]:
                        out.sounds.append(self.rng.choice(cfg["idle_sounds"]))

        out.state = self.state
        out.hold = self.state in ("look", "greet")
        out.heading = self.heading
        out.home_dist = None if home is None else home[0]
        out.dome = self._dome(now, best, waiting, dome_deg)
        return out


def wander_active(mode, auto_on):
    """Does the head run? Patrol or Free roam, with the autonomous mode on."""
    return bool(auto_on) and mode in WANDER_MODES


def head_plan(was, mode):
    """What the wander node does with its head when the mode it runs for (None: none) becomes `mode`:
    "start" a new one, "keep" it, "restart" (Patrol <-> Free roam: a new start and radius, the dome
    keeps going), "stop" (one stop for the dome) or stay "idle"."""
    if was is None:
        return "idle" if mode is None else "start"
    if mode is None:
        return "stop"
    return "keep" if mode == was else "restart"
