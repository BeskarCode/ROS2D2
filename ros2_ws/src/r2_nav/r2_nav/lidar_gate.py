# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""A mode waits for the lidar before moving the feet.

With the lidar's motor set to with_modes it only spins while a mode is on, so a mode that just
started holds still until a scan arrives, or WAIT_S passes; then it drives as it always did
without a lidar (with the Pico's sensors). With always or off it never waits.
"""

WAIT_S = 5.0                    # the C1 takes about 4 s from start_motor to its first scan


class LidarGate:
    def __init__(self, policy="always"):
        self.policy = policy
        self.since = None           # when the mode started
        self.seen = False           # a scan arrived since then

    def activate(self, now):
        self.since, self.seen = now, False

    def reset(self):
        self.since, self.seen = None, False

    def on_scan(self, now):
        if self.since is not None and now >= self.since:
            self.seen = True

    def ready(self, now):
        if self.policy != "with_modes":
            return True
        return self.since is not None and (self.seen or now - self.since >= WAIT_S)


def motor_policy(sensors):
    """The lidar's motor setting in sensors.yaml (always when there is no lidar)."""
    for s in sensors.values():
        if s.get("type") == "rplidar_c1":
            return s.get("motor", "always")
    return "always"
