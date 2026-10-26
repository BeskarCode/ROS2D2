"""Lidar scans without ROS: cut a scan to the angles the droid does not hide, and a
pretend room for the simulated lidar."""

import math

# The simulated room, in base_link (x forward, y left): four walls and a chair leg
WALLS = {"front": 2.0, "back": -1.5, "left": 1.5, "right": -1.5}
POSTS = [(0.8, 0.3, 0.02)]   # (x, y, radius)


def crop(ranges, angle_min, angle_increment, lower, upper):
    """Rays outside [lower, upper] (radians) become inf: the droid's own body is there."""
    out = []
    for i, r in enumerate(ranges):
        a = angle_min + i * angle_increment
        out.append(r if lower - 1e-9 <= a <= upper + 1e-9 else math.inf)
    return out


def _hit(ox, oy, dx, dy):
    """Distance along the unit ray (dx, dy) from (ox, oy) to the nearest wall or post."""
    best = math.inf
    if dx > 1e-12:
        best = min(best, (WALLS["front"] - ox) / dx)
    if dx < -1e-12:
        best = min(best, (WALLS["back"] - ox) / dx)
    if dy > 1e-12:
        best = min(best, (WALLS["left"] - oy) / dy)
    if dy < -1e-12:
        best = min(best, (WALLS["right"] - oy) / dy)
    for px, py, pr in POSTS:
        fx, fy = px - ox, py - oy
        along = fx * dx + fy * dy
        off2 = fx * fx + fy * fy - along * along
        if along > 0 and off2 <= pr * pr:
            best = min(best, along - math.sqrt(pr * pr - off2))
    return best


def fake_ranges(origin, yaw, angles, range_max):
    """What a lidar at origin (x, y in base_link), turned yaw radians, reads at each angle."""
    ox, oy = origin
    out = []
    for a in angles:
        d = _hit(ox, oy, math.cos(yaw + a), math.sin(yaw + a))
        out.append(d if d <= range_max else math.inf)
    return out
