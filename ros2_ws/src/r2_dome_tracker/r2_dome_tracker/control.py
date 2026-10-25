"""Dome tracking control law, ported from the proof of concept (DomeTracker/poc).

No ROS here, so it can be unit-tested and tuned on its own.

Units:
  error  -1 (face at the left edge) .. 0 (centre) .. +1 (right edge)
  speed  ShadowMD DM: units, signed; 0 = stop
"""

from dataclasses import dataclass


@dataclass
class Gains:
    min_speed: int = 18      # speed just outside the dead zone
    max_speed: int = 58      # speed with the face at the edge
    kd: float = 0.3          # how much the face's own speed counts, in seconds
    deadzone: float = 0.15   # centre band with no movement, 0-1
    invert: bool = True      # turn the other way (on for the droid the PoC was tuned on)
    lost_after: float = 0.2  # no face for this long -> dome stops, seconds


class DomeTracker:
    def __init__(self, gains=None):
        self.gains = gains or Gains()
        self.reset()

    def reset(self):
        self.smooth_err = 0.0
        self.rate = 0.0          # how fast the face moves across the picture, halves per second
        self.prev_err = None
        self.prev_t = 0.0
        self.last_face_t = None

    def face(self, err, t):
        """A picture taken at time t had the face at err."""
        self.smooth_err = 0.5 * self.smooth_err + 0.5 * err      # calm the jitter between frames
        if self.prev_err is not None and 0 < t - self.prev_t < 0.2:
            self.rate = 0.6 * self.rate + 0.4 * (err - self.prev_err) / (t - self.prev_t)
        self.prev_err, self.prev_t = err, t
        self.last_face_t = t

    def no_face(self):
        """A picture without a face."""
        self.smooth_err = 0.0
        self.rate = 0.0
        self.prev_err = None

    def has_target(self, now):
        return self.last_face_t is not None and now - self.last_face_t <= self.gains.lost_after

    def speed(self, now):
        """DM: speed for this moment."""
        g = self.gains
        if not self.has_target(now):
            return 0
        # Where the face is plus where it is heading: moving out speeds the dome up,
        # coming back to the centre (the dome catching up) brakes it before it overshoots.
        u = self.smooth_err + g.kd * self.rate
        if abs(u) < g.deadzone or (u > 0) != (self.smooth_err > 0):
            return 0
        frac = min((abs(u) - g.deadzone) / (1 - g.deadzone), 1.0)
        mag = g.min_speed + (g.max_speed - g.min_speed) * frac
        return int(round(mag)) * (1 if u > 0 else -1) * (-1 if g.invert else 1)


def face_error(center_x, width):
    """Pixel column of the face centre -> -1 .. +1."""
    return (center_x - width / 2) / (width / 2)


SPEED_REF = 80   # ShadowMDLite's DOME_TRACKER_MAX_SPEED: deg_per_s_at_80 is measured here


class DomeEstimate:
    """Dome angle worked out from the speeds sent (the dome has no position sensor).

    Degrees, + = turned right (towards a face with a positive error), wrapped to -180..180.
    """

    def __init__(self, deg_per_s_at_80=90.0):
        self.deg_per_s_at_80 = deg_per_s_at_80
        self.reset()

    def reset(self):
        self.angle = 0.0

    def update(self, speed, invert, dt):
        # The tracker flips the sign with invert, so flip it back to get the real direction
        direction = -1 if invert else 1
        self.angle += direction * speed / SPEED_REF * self.deg_per_s_at_80 * dt
        self.angle = (self.angle + 180.0) % 360.0 - 180.0


REF_HALF_FOV = 30.0   # degrees off centre that count as error 1 (the gains were tuned on a 60 deg camera)


def bearing_deg(err, yaw_deg, hfov_deg):
    """Face error in one camera's picture -> degrees from the dome's front (+ = right)."""
    return yaw_deg + err * hfov_deg / 2


def in_view(rel_deg, cameras):
    """Whether a direction (degrees from the dome's front) falls in any camera's view.

    cameras: iterable of (yaw_deg, hfov_deg).
    """
    return any(abs(rel_deg - yaw) <= hfov / 2 for yaw, hfov in cameras)


def pick_face(latest, now, max_age):
    """The face to follow among several cameras: the biggest one seen recently.

    latest: {camera: (t, bearing_deg, size)} with the newest face of each camera, size as a
    fraction of the picture width (so cameras with different resolutions compare fairly).
    Returns (t, bearing_deg) or None.
    """
    fresh = [v for v in latest.values() if v is not None and now - v[0] <= max_age]
    if not fresh:
        return None
    t, bearing, _ = max(fresh, key=lambda v: v[2])
    return t, bearing


def face_to_error(bearing, dome_deg, cameras, simulate):
    """Bearing of a face (degrees, from where the cameras point now) -> tracker error.

    With simulate the cameras stay still but pretend to turn with the (estimated) dome:
    the face is shifted by the dome angle and dropped if no camera would see it any more.
    """
    rel = bearing - dome_deg if simulate else bearing
    if simulate and not in_view(rel, cameras):
        return None
    return rel / REF_HALF_FOV
