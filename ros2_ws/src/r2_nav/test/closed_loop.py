# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The whole loop without ROS, for tests and debugging: the simulated room and sensors (r2_sim),
the navigator (nav_core), the nodes' own inputs and ramps (shaping), and the bridge's unit conversion and limits.
Deterministic with a seed. drive(...) returns the trace:
(t, state, tries, x, y, heading deg, why, bump, v, w) per step; bump = it drove into something,
v and w = what reached the feet."""
import math

from r2_nav.follow_core import Follower
from r2_nav.modes import parse_modes
from r2_nav.nav_core import Navigator, parse_nav
from r2_nav.shaping import SensorInputs, shape
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
    """goal: (x, y) for Go to a point, or None for Go forward (along R2's heading)."""
    cfg = cfg or parse_nav("")
    nav = Navigator(cfg, sensors)
    if goal is None:
        nav.start_forward(world.pose[2])
    else:
        nav.set_goal(*goal)
    sim = SensorSim(seed)
    inputs = SensorInputs()
    v_out = w_out = 0.0
    trace = []
    lidar = next(s for s in sensors.values() if s["type"] == "rplidar_c1")
    t = 0.0
    while t < seconds:
        pose = tuple(world.pose)
        for n, s in sensors.items():
            if s["type"] != "rplidar_c1":
                inputs.on_range(n, t, sim.range_of(world, pose, s), cfg["filter"])
        snap = inputs.snapshot(t)
        d = nav.step(t, pose, lidar_points(sim, world, pose, lidar), snap.ranges, True, speed=v_out, lost=snap.lost)
        v_out, w_out = shape((v_out, w_out), d.v, d.w, d.hard_stop, cfg, dt)
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


def wander_run(world, sensors, mode, seconds=180.0, seed=1, dt=0.1, cfg=None):
    """Patrol ("patrol") or Free roam ("free") round the simulated room: the head (wander_core) gives
    the course, the navigator drives it. No faces. Rows: (t, nav state, x, y, distance to the start,
    bump, v, head state)."""
    import random

    from r2_dome_tracker.control import Gains
    from r2_nav.wander_core import Wander
    cfg = cfg or parse_nav("")
    nav = Navigator(cfg, sensors)
    nav.wandering = True
    head = Wander(cfg["wander"], Gains(), random.Random(seed), mode == "patrol")
    head.start(0.0, tuple(world.pose))
    x0, y0 = world.pose[0], world.pose[1]
    sim = SensorSim(seed)
    inputs = SensorInputs()
    v_out = w_out = 0.0
    nav_state = None
    rows = []
    lidar = next(s for s in sensors.values() if s["type"] == "rplidar_c1")
    t = 0.0
    while t < seconds:
        pose = tuple(world.pose)
        out = head.step(t, pose, nav_state, [], 0.0)
        nav.steer(out.heading, out.hold)
        for n, s in sensors.items():
            if s["type"] != "rplidar_c1":
                inputs.on_range(n, t, sim.range_of(world, pose, s), cfg["filter"])
        snap = inputs.snapshot(t)
        d = nav.step(t, pose, lidar_points(sim, world, pose, lidar), snap.ranges, True, speed=v_out, lost=snap.lost)
        nav_state = d.state
        v_out, w_out = shape((v_out, w_out), d.v, d.w, d.hard_stop, cfg, dt)
        drive_u, turn_u = twist_to_units(v_out, w_out, DRIVE, TURN, MAX_LIN, MAX_ANG)
        v, w = units_to_twist(drive_u, turn_u, DRIVE, TURN)
        nxt = step_pose(world.pose, v, w, dt)
        bump = blocked_move(world, nxt) and v != 0
        if bump:
            nxt = (world.pose[0], world.pose[1], nxt[2])
        world.pose = list(nxt)
        rows.append((round(t, 1), d.state, world.pose[0], world.pose[1],
                     math.hypot(world.pose[0] - x0, world.pose[1] - y0), bump, v, out.state))
        t += dt
    return rows
