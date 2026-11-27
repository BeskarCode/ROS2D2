# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Lidar scans without ROS: cut a scan to the angles the droid does not hide, and a
pretend room for the simulated lidar."""

import math

# The simulated room, in base_link (x forward, y left): four walls and a chair leg
WALLS = {"front": 2.0, "back": -1.5, "left": 1.5, "right": -1.5}
POSTS = [(0.8, 0.3, 0.02)]   # (x, y, radius)


def _wrap(a):
    """An angle in (-pi, pi]: a driver may give its scan from 0 to 2 pi."""
    return math.atan2(math.sin(a), math.cos(a))


def crop(ranges, angle_min, angle_increment, lower, upper):
    """Rays outside [lower, upper] (radians, within -pi..pi) become inf: the droid's own body is there."""
    out = []
    for i, r in enumerate(ranges):
        a = angle_min + i * angle_increment
        inside = lower - 1e-9 <= a <= upper + 1e-9 or lower - 1e-9 <= _wrap(a) <= upper + 1e-9
        out.append(r if inside else math.inf)
    return out


def mask(ranges, angle_min, angle_increment, sectors):
    """Rays inside any sector (radians, from -> to counter-clockwise; from > to crosses +-pi)
    become inf: there the lidar sees R2 itself."""
    def inside(a, lo, hi):
        a = math.atan2(math.sin(a), math.cos(a))
        if lo <= hi:
            return lo - 1e-9 <= a <= hi + 1e-9
        return a >= lo - 1e-9 or a <= hi + 1e-9
    out = []
    for i, r in enumerate(ranges):
        a = angle_min + i * angle_increment
        out.append(math.inf if any(inside(a, lo, hi) for lo, hi in sectors) else r)
    return out


def blanked(n, angle_min, angle_increment, lower, upper, sectors):
    """The indices of the rays crop() and mask() turn into inf, for a scan of n rays: worked out
    once per scan geometry and setting, then written in place on every scan."""
    ones = [1.0] * n
    kept = mask(crop(ones, angle_min, angle_increment, lower, upper), angle_min, angle_increment, sectors)
    return tuple(i for i, r in enumerate(kept) if r != 1.0)


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
