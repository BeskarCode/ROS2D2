# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""What the IMU node counts and tells the console (pure: no ROS).

Stats keeps the last second: frames a second, the strongest knock (acceleration without gravity) and the
chip's raw roll and pitch for "Level here". status() is the /imu/status JSON. sim_sample() is a pretend
BNO085 (simulate:=true) that moves like the console's mock: to try the tab with no board.
"""

import json
import math
from collections import deque

from r2_imu_bno085.calib import linear_accel
from r2_imu_bno085.rvc import Sample

WINDOW = 1.0      # seconds


class Stats:
    def __init__(self):
        self._frames = deque()      # (t, |linear acceleration|)
        self._raw = deque()         # (t, roll, pitch) of the chip

    @staticmethod
    def _trim(q, now):
        while q and q[0][0] <= now - WINDOW:
            q.popleft()

    def frame(self, t, r2_pitch, r2_roll, accel_r2):
        lin = linear_accel(r2_pitch, r2_roll, accel_r2)
        self._frames.append((t, math.sqrt(sum(v * v for v in lin))))
        self._trim(self._frames, t)

    def raw(self, t, roll, pitch):
        self._raw.append((t, roll, pitch))
        self._trim(self._raw, t)

    def fps(self, now):
        self._trim(self._frames, now)
        return len(self._frames)

    def bump(self, now):
        self._trim(self._frames, now)
        return max((m for _, m in self._frames), default=0.0)

    def last_second(self, now):
        self._trim(self._raw, now)
        return [(r, p) for _, r, p in self._raw]


def _r2(v):
    return None if v is None else round(v, 2)


def status(*, connected, port, fps, bad_frames, cfg, last_frame_age, bump, simulate, error):
    """The /imu/status JSON the console reads (twice a second)."""
    return json.dumps({
        "connected": connected, "port": port, "fps": fps, "bad_frames": bad_frames,
        "levelled": cfg["level"] is not None, "level": cfg["level"], "box": cfg["box"], "front": cfg["front"],
        "in_use": cfg["in_use"], "invert_yaw": cfg["invert_yaw"], "last_frame_age": _r2(last_frame_age),
        "bump": _r2(bump), "simulate": simulate, "error": error,
    })


def sim_sample(t, index):
    """A pretend frame at time t: R2 turning slowly, tilting a little, being pushed about."""
    roll, pitch = 6.0 * math.sin(t * 0.7), 12.0 * math.sin(t * 0.45)
    yaw = (12.0 * t + 180.0) % 360.0 - 180.0
    still = linear_accel(pitch, roll, (0.0, 0.0, 0.0))            # minus gravity as felt at that tilt
    push = (1.2 * math.sin(t * 1.3), 0.8 * math.sin(t * 0.9 + 1.0), 0.3 * math.sin(t * 2.1))
    accel = tuple(-still[i] + push[i] for i in range(3))
    return Sample(index=index & 0xFF, yaw=yaw, pitch=pitch, roll=roll, accel=accel)
