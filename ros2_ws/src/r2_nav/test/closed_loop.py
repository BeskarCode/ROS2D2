# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The whole loop without ROS, for tests and debugging: the simulated room and sensors (r2_sim),
the navigator (nav_core), the node's filter and ramps, and the bridge's unit conversion and limits.
Deterministic with a seed. drive(...) returns the trace:
(t, state, tries, x, y, heading deg, why, bump, v, w) per step; bump = it drove into something,
v and w = what reached the feet."""
import math

from r2_nav.follow_core import Follower
from r2_nav.modes import parse_modes
from r2_nav.nav_core import Navigator, RangeFilter, parse_nav, ramp
from r2_sim.world import SensorSim, World, blocked_move, sensor_pose, step_pose
from r2_shadow_bridge.protocol import twist_to_units, units_to_twist

DRIVE, TURN, MAX_LIN, MAX_ANG = 50.0, 30.0, 0.4, 0.6     # the bridge's defaults


def lidar_points(sim, world, pose, lidar):
    a0, inc, ranges = sim.scan(world, pose, lidar, 1.0)
    half = math.radians(lidar["fov_deg"] / 2)
    pts = []
    for i, r in enumerate(ranges):
        a = a0 + i * inc
        if math.isfinite(r) and abs(a) <= half + 1e-9:
            yaw = math.radians(lidar["yaw_deg"])
            pts.append((lidar["x"] + r * math.cos(a + yaw), lidar["y"] + r * math.sin(a + yaw)))
    return pts


def drive(world, sensors, goal, cfg=None, seconds=120.0, seed=1, dt=0.1):
    cfg = cfg or parse_nav("")
    nav = Navigator(cfg, sensors)
    nav.set_goal(*goal)
    sim = SensorSim(seed)
    filters = {}
    v_out = w_out = 0.0
    trace = []
    lidar = next(s for s in sensors.values() if s["type"] == "rplidar_c1")
    t = 0.0
    while t < seconds:
        pose = tuple(world.pose)
        ranges = {}
        for n, s in sensors.items():
            if s["type"] == "rplidar_c1":
                continue
            r = sim.range_of(world, pose, s)
            ranges[n] = filters.setdefault(n, RangeFilter()).update(r) if cfg["filter"] else r
        d = nav.step(t, pose, lidar_points(sim, world, pose, lidar), ranges, True, speed=v_out)
        v_out = ramp(v_out, d.v, cfg["accel"] * dt)
        w_out = ramp(w_out, d.w, math.radians(cfg["turn_accel_deg"]) * dt)
        if d.state == "stop" and d.v == 0:
            v_out = min(v_out, 0.0)
        if not cfg["allow_reverse"]:
            v_out = max(0.0, v_out)
        drive_u, turn_u = twist_to_units(v_out, w_out, DRIVE, TURN, MAX_LIN, MAX_ANG)
        v, w = units_to_twist(drive_u, turn_u, DRIVE, TURN)
        nxt = step_pose(world.pose, v, w, dt)
        bump = blocked_move(world, nxt) and v != 0
        if bump:
            nxt = (world.pose[0], world.pose[1], nxt[2])
        world.pose = list(nxt)
        trace.append((round(t, 1), d.state, d.tries, round(world.pose[0], 2), round(world.pose[1], 2),
                      round(math.degrees(world.pose[2])), d.why, bump, v, w))
        if d.state in ("arrived", "gave up"):
            break
        t += dt
    return trace


def follow(world, sensors, person_at, seconds=40.0, seed=1, dt=0.1, cfg=None, fcfg=None):
    """Follow a colour round the simulated room. person_at(t) -> (x, y) of the obstacle wearing the
    shirt. Returns rows (t, state, x, y, distance to the person, bump, v)."""
    cfg = cfg or parse_nav("")
    fcfg = fcfg or parse_modes("")["follow"]
    fol = Follower(fcfg, cfg, sensors)
    sim = SensorSim(seed)
    lidar = next(s for s in sensors.values() if s["type"] == "rplidar_c1")
    person = next(o for o in world.obstacles if o.get("marker"))
    fol.start(0.0)
    trace = []
    t = 0.0
    while t < seconds:
        person["x"], person["y"] = person_at(t)
        pose = tuple(world.pose)
        view = world.marker_view(pose)
        marker = None if view is None else dict(view, t=t)
        ranges = {n: sim.range_of(world, pose, s) for n, s in sensors.items() if s["type"] != "rplidar_c1"}
        d = fol.step(t, marker, lidar_points(sim, world, pose, lidar), ranges)
        drive_u, turn_u = twist_to_units(d.v, d.w, DRIVE, TURN, MAX_LIN, MAX_ANG)
        v, w = units_to_twist(drive_u, turn_u, DRIVE, TURN)
        nxt = step_pose(world.pose, v, w, dt)
        bump = blocked_move(world, nxt) and v != 0
        if bump:
            nxt = (world.pose[0], world.pose[1], nxt[2])
        world.pose = list(nxt)
        trace.append((round(t, 1), d.state, world.pose[0], world.pose[1],
                      math.hypot(person["x"] - world.pose[0], person["y"] - world.pose[1]), bump, v))
        t += dt
    return trace
