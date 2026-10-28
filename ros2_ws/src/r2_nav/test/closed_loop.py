# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The whole loop without ROS, for tests and debugging: the simulated room and sensors (r2_sim),
the navigator (nav_core), the node's filter and ramps, and the bridge's unit conversion and limits.
Deterministic with a seed. drive(...) returns the trace:
(t, state, tries, x, y, heading deg, why, bump) per step; bump = it drove into something."""
import math

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
        d = nav.step(t, pose, lidar_points(sim, world, pose, lidar), ranges, True)
        v_out = ramp(v_out, d.v, cfg["accel"] * dt)
        w_out = ramp(w_out, d.w, 2.5 * dt)
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
                      round(math.degrees(world.pose[2])), d.why, bump))
        if d.state in ("arrived", "gave up"):
            break
        t += dt
    return trace
