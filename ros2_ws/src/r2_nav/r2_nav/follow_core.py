# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Follow a colour, without ROS: drive towards the colour marker the dome camera sees (/marker)
and stay `distance` m behind it. Same safety as the navigator (nav_core): the safety circle,
slowing down from slow_from, the front sensors' stop distances plus braking, the floor sensor.
It never backs up. If the marker is lost it stops at once, looks around with the dome for
search_s seconds (ending facing forward) and then waits, still. Boxed in, it only says so.

Frames as in nav_core: base_link, x forward, y left, + angle = left. The marker's bearing is
relative to the droid (the dome looks forward while following). The ramps (accel,
turn_accel_deg from nav.yaml) are applied here: what step() returns goes to the feet as is.
"""

import math
from dataclasses import dataclass, field

from r2_nav.nav_core import (DRIVE_UNITS_PER_MPS, SIDE_SLOW_MIN, TURN_UNITS_PER_RADPS, braking, choose_heading,
                             clearance, floor_problem, is_floor, is_lidar, nearest_ahead, points_from, ramp, wrap,
                             stop_distances)

STALE = 0.3                  # s: an older marker counts as lost
K_TURN = 1.2                 # rad/s per rad of bearing
K_SPEED = 0.6                # m/s per metre further than `distance`
NEAR = 0.15                  # m: closer than distance + NEAR it waits
CONE = math.radians(6)       # lidar points this close to the bearing are the person
CONE_MAX = 4.0               # m: further lidar points are not the person
DOME_SEARCH = 25             # DM: units while looking around
BLOCKED_AFTER = 4.0          # s blocked before saying so
BLOCKED_REPEAT = 15.0        # s between two "blocked" while it lasts
TURN_ROOM = 0.4              # m: something closer than this to the centre and it does not even turn
WIGGLE = 2.0                 # s of dome side to side each time it says it is blocked
GRACE = 1.0                  # s after start(): no marker yet is not "lost" (the camera needs a moment)
STATES = ("following", "waiting", "blocked", "searching", "lost", "recentring", "no data")


def sweep(e, length):
    """Dome units for a look round of `length` s, e s in: + a quarter, - half, + a quarter (net 0)."""
    q = length / 4
    return DOME_SEARCH if e < q or e >= 3 * q else -DOME_SEARCH


@dataclass
class FollowDecision:
    v: float = 0.0
    w: float = 0.0
    dome: int = 0
    state: str = "no data"
    events: list = field(default_factory=list)


class Follower:
    def __init__(self, follow_cfg, nav_cfg, sensors):
        self.fcfg, self.cfg, self.sensors = follow_cfg, nav_cfg, sensors
        self.v = self.w = 0.0
        self.last_t = None
        self.lost_since = None       # when the marker went missing (None = seeing it)
        self.blocked_since = None
        self.next_blocked = None     # when the next "blocked" event is due
        self.floor_seen = set()
        self.offset = 0.0            # DM: units x s it has turned the dome away from the front
        self.dome = 0                # what it asked of the dome last step
        self.wiggle_since = None     # dome side to side after saying it is blocked
        self.dt = 0.1
        self.entered = None          # set by start(): until the first marker or GRACE, silence

    def start(self, now):
        """Follow has just been switched on: give the camera GRACE s to deliver a first marker."""
        self.entered = now

    def reconfigure(self, follow_cfg=None, nav_cfg=None, sensors=None):
        self.fcfg = follow_cfg or self.fcfg
        self.cfg = nav_cfg or self.cfg
        self.sensors = sensors or self.sensors

    def _front(self):
        return [n for n, s in self.sensors.items() if not is_lidar(s) and not is_floor(s) and abs(s["yaw_deg"]) < 90]

    def _distance(self, bearing, area, scan_xy):
        """Metres to the person: the nearest lidar point near the bearing, else from the marker's size."""
        f = self.fcfg
        size = None
        if f.get("area_ref") and area and area > 0:
            size = f["distance"] * math.sqrt(f["area_ref"] / area)
        lidar = min((math.hypot(x, y) for x, y in scan_xy or []
                     if math.hypot(x, y) <= CONE_MAX and abs(wrap(math.atan2(y, x) - bearing)) <= CONE), default=None)
        # something much nearer than the marker's size says is in the way, not the person
        if lidar is not None and size is not None and lidar < f["distance"] and size > 2 * lidar:
            return size
        return lidar if lidar is not None else size

    def _stop(self, d, state):
        self.v = self.w = 0.0
        d.v = d.w = 0.0
        d.state = state
        return d

    def _recentre(self, d):
        """Dome units that bring it back to the front (0 once there). The marker's bearing is
        relative to the camera: it only follows with the dome facing forward."""
        if self.dt <= 0 or round(self.offset / self.dt) == 0:
            return False
        d.dome = int(max(-DOME_SEARCH, min(DOME_SEARCH, round(-self.offset / self.dt))))
        return True

    def step(self, now, marker, scan_xy, ranges):
        """One decision. marker: the /marker dict or None; scan_xy: lidar points in base_link or
        None when the lidar is silent; ranges: {name: metres | None} of the sensors reporting."""
        dt = 0.1 if self.last_t is None else max(0.0, min(0.5, now - self.last_t))
        self.last_t, self.dt = now, dt
        self.offset += self.dome * dt
        d = self._step(now, marker, scan_xy, ranges, dt)
        self.dome = d.dome
        return d

    def _step(self, now, marker, scan_xy, ranges, dt):
        cfg, f = self.cfg, self.fcfg
        d = FollowDecision()
        front = self._front()
        if scan_xy is None and not any(n in ranges for n in front):
            self.blocked_since = self.wiggle_since = None
            return self._stop(d, "no data")

        # ---- just started and no marker yet: wait still, silently, before calling it lost
        if marker is None and self.entered is not None and now - self.entered < GRACE:
            self.blocked_since = self.wiggle_since = None
            return self._stop(d, "waiting")
        if marker is not None:
            self.entered = None

        # ---- lost: stop, look around with the dome, then wait still
        seen = marker is not None and marker.get("seen") and now - marker.get("t", -math.inf) <= STALE
        if not seen:
            self.blocked_since = self.wiggle_since = None
            if self.lost_since is None:
                self.lost_since = now
                d.events.append("lost")
            e, s = now - self.lost_since, f["search_s"]
            if e < s:
                d.dome = sweep(e, s)
                return self._stop(d, "searching")
            self._recentre(d)
            return self._stop(d, "lost")
        if self.lost_since is not None:
            d.events.append("found")
        self.lost_since = None
        if self.wiggle_since is not None and now - self.wiggle_since < WIGGLE:
            d.dome = sweep(now - self.wiggle_since, WIGGLE)
            return self._stop(d, "blocked")
        self.wiggle_since = None
        if self._recentre(d):
            return self._stop(d, "recentring")

        # ---- what it would like to do
        bearing = marker["bearing"]
        dist = self._distance(bearing, marker.get("area"), scan_xy)
        wm = min(math.radians(cfg["max_turn_deg"]), cfg["max_turn_power"] / TURN_UNITS_PER_RADPS)
        vmax = min(f["max_speed"], cfg["max_drive_power"] / DRIVE_UNITS_PER_MPS)
        v_want = 0.0
        if dist is not None and dist >= f["distance"] + NEAR:
            v_want = min(vmax, K_SPEED * (dist - f["distance"]))

        # ---- safety, as the navigator: the way along the bearing, else the best free heading
        R = cfg["safety_radius"]
        pts = points_from(scan_xy, ranges, self.sensors)
        direct = clear = clearance(pts, bearing)
        heading = bearing
        # something in the way (not the person) before slow_from: steer round it like the navigator
        if R <= direct < R + cfg["slow_from"] and not (dist is not None and direct >= dist - 0.1):
            heading, clear = choose_heading(pts, bearing, cfg)
        stops = stop_distances(self.sensors, cfg)
        brake = braking(self.v, cfg)
        too_close = any(ranges.get(n) is not None and stops[n] > 0 and ranges[n] < stops[n] + brake for n in front)
        for n, s in self.sensors.items():
            if is_floor(s) and ranges.get(n) is not None:
                self.floor_seen.add(n)
            if is_floor(s) and n in self.floor_seen and n in ranges and floor_problem(s, ranges[n]):
                too_close = True
        slow = lambda x: max(0.0, min(1.0, (x - R) / cfg["slow_from"]))   # noqa: E731
        v_want = min(v_want, vmax * min(slow(clear), max(SIDE_SLOW_MIN, slow(nearest_ahead(pts))))
                     * max(0.0, math.cos(heading)))
        # the way to the person is shut inside the safety circle: stop (it does not go round)
        blocked = (too_close or direct < R or clear < R) and dist is not None and dist >= f["distance"] + NEAR

        # ---- boxed in: say so after a while, and again now and then; nothing else
        if blocked:
            if self.blocked_since is None:
                self.blocked_since, self.next_blocked = now, now + BLOCKED_AFTER
            if now >= self.next_blocked - 1e-9:
                d.events.append("blocked")
                self.next_blocked += BLOCKED_REPEAT
                self.wiggle_since = now
                d.dome = sweep(0.0, WIGGLE)
        else:
            self.blocked_since = None

        room = all(math.hypot(x, y) > TURN_ROOM for x, y in pts)
        if blocked or too_close:
            self.v = 0.0                                           # a stop is a stop: no ramp down
            w_want = max(-wm, min(wm, K_TURN * bearing)) if room else 0.0
            d.state = "blocked" if blocked else "waiting"
        else:
            w_want = max(-wm, min(wm, K_TURN * (heading if v_want > 0 else bearing)))
            d.state = "following" if v_want > 0 else "waiting"
        self.v = max(0.0, ramp(self.v, v_want if not (blocked or too_close) else 0.0, cfg["accel"] * dt))
        self.w = ramp(self.w, w_want, math.radians(cfg["turn_accel_deg"]) * dt)
        if not room:
            self.w = 0.0
        d.v, d.w = self.v, self.w
        return d
