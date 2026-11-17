# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Odometry without wheel encoders (dead reckoning), without ROS.

Where R2 is, worked out from what really went to the Mega: each ROS:FOOT:<drive>,<turn> line on
/mega/tx (the bridge's own copy of what it wrote), turned into m/s and rad/s with the bridge's
calibration (foot_calibrate), held for FOOT_LASTS like the Mega's own watchdog. The heading comes
from the IMU (/imu/data, Madgwick, no magnetometer) when it is fresh: much better than the
commanded turn on a floor where the feet slip. x, y drift with every slip: good enough for goals
a few metres away indoors; a laser odometry (rf2o) or encoders later correct it.
"""
import math
import re

FOOT = re.compile(r"^ROS:FOOT:(-?\d+),(-?\d+)$")
FOOT_LASTS = 0.3          # s: the Mega stops the feet after this without a new command
IMU_STALE = 0.5           # s: an older IMU heading is not used


def parse_foot(line):
    """(drive, turn) units from a ROS:FOOT: line, else None."""
    m = FOOT.match(line.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def yaw_of(qx, qy, qz, qw):
    return math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


class DeadReckoning:
    def __init__(self, drive_per_mps=50.0, turn_per_radps=30.0):
        self.drive_per_mps, self.turn_per_radps = drive_per_mps, turn_per_radps
        self.x = self.y = self.th = 0.0
        self.v = self.w = 0.0
        self.foot = None          # (time, drive, turn)
        self.imu = None           # (time, yaw)
        self.imu_offset = None    # odom heading = IMU yaw + offset (set the first time the IMU is used)
        self.last = None

    def on_foot(self, now, drive, turn):
        self.foot = (now, drive, turn)

    def on_imu(self, now, yaw):
        self.imu = (now, yaw)

    def step(self, now):
        """Integrate up to `now`; returns (x, y, th, v, w)."""
        if self.last is None:
            self.last = now
            return self.x, self.y, self.th, 0.0, 0.0
        dt = max(0.0, min(0.5, now - self.last))
        self.last = now
        v = w = 0.0
        if self.foot and now - self.foot[0] < FOOT_LASTS:
            v, w = self.foot[1] / self.drive_per_mps, self.foot[2] / self.turn_per_radps
        th0 = self.th
        if self.imu and now - self.imu[0] < IMU_STALE:
            if self.imu_offset is None:
                self.imu_offset = wrap(self.th - self.imu[1])
            th1 = wrap(self.imu[1] + self.imu_offset)
            if dt > 0:
                w = wrap(th1 - th0) / dt              # what it really turned
        else:
            self.imu_offset = None                    # back on the IMU later: start from where we are
            th1 = wrap(th0 + w * dt)
        mid = th0 + wrap(th1 - th0) / 2
        self.x += v * dt * math.cos(mid)
        self.y += v * dt * math.sin(mid)
        self.th, self.v, self.w = th1, v, w
        return self.x, self.y, self.th, v, w
