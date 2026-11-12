# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""When the lidar's motor spins, apart from ROS so it can be tested.

sensors.yaml's lidar motor: always | with_modes (only while an automatic mode is on) | off.
with_modes keeps it spinning LINGER_S after the last mode goes off, so switching modes never
stops and restarts it.
"""

MODES = ("goto", "forward", "patrol", "follow")
LINGER_S = 5.0


def mode_active(auto_on, mode):
    """An automatic mode is on: /r2/auto_mode true and /r2/mode one of the driving modes (no
    /r2/mode yet = an old bridge: goto, as drives_in says)."""
    return bool(auto_on) and (mode is None or mode in MODES)


class MotorPolicy:
    """update() says what to ask the driver for: "start", "stop" or None (nothing new)."""

    def __init__(self):
        self.sent = None            # the last order sent
        self.off_since = None       # when the modes went off (after having been on)

    def driver_restarted(self):
        """The driver started again (it always starts spinning): the next update says it again."""
        self.sent = None

    def update(self, now, policy, active):
        if active:
            self.off_since = None
        elif self.sent == "start" and self.off_since is None:
            self.off_since = now
        if policy == "always":
            want = "start"
        elif policy == "off":
            want = "stop"
        elif active or (self.off_since is not None and now - self.off_since < LINGER_S):
            want = "start"
        else:
            want = "stop"
        if want == self.sent:
            return None
        self.sent = want
        return want
