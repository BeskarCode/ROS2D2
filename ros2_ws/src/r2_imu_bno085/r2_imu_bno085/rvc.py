# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The BNO085's UART-RVC frames, read without ROS (pure: tested on the PC).

In UART-RVC mode (P0 high) the BNO085 does the sensor fusion itself and sends, on its own, frames
of 19 bytes, little-endian:

    0xAA 0xAA  index  yaw  pitch  roll  ax  ay  az  r1 r2 r3  checksum
               uint8  int16 x3, 0.01 degree  int16 x3, mg   unused  sum of the 16 bytes from index

There is no gyro rate in the frame: yaw_rate() works it out from two yaws.
"""

import math
import struct
from dataclasses import dataclass

HEADER = b"\xaa\xaa"
BODY_LEN = 17
FRAME_LEN = len(HEADER) + BODY_LEN
G_PER_MG = 9.80665 / 1000.0          # m/s^2 per mg

_BODY = struct.Struct("<BhhhhhhBBBB")


@dataclass
class Sample:
    index: int
    yaw: float           # degrees, -180..180
    pitch: float
    roll: float
    accel: tuple         # m/s^2, x y z


def frame_bytes(index, yaw, pitch, roll, ax_mg, ay_mg, az_mg):
    """Build a frame (for tests and the fake sensor). Angles in degrees, acceleration in mg."""
    body = _BODY.pack(index & 0xFF, round(yaw * 100), round(pitch * 100), round(roll * 100),
                      ax_mg, ay_mg, az_mg, 0, 0, 0, 0)
    body = body[:16] + bytes([sum(body[:16]) & 0xFF])
    return HEADER + body


class RvcParser:
    """Feed it whatever the serial port gives; it returns the whole, good frames.
    A frame only counts if its checksum agrees, so 0xAA 0xAA inside the data does not fool it."""

    def __init__(self):
        self.buf = bytearray()
        self.bad = 0                     # frames dropped for a wrong checksum

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            at = self.buf.find(HEADER)
            if at < 0:
                del self.buf[:-1]        # keep a lone 0xAA: the other half may come next
                return out
            if len(self.buf) - at < FRAME_LEN:
                del self.buf[:at]
                return out
            body = bytes(self.buf[at + 2:at + FRAME_LEN])
            if sum(body[:16]) & 0xFF != body[16]:
                # 0xAA 0xAA 0xAA: a stray 0xAA before the real header (or index 0xAA). Try one
                # byte on before calling it bad; wait for that byte if it has not come yet.
                if body[0] == 0xAA:
                    if len(self.buf) - at < FRAME_LEN + 1:
                        del self.buf[:at]
                        return out
                    nxt = bytes(self.buf[at + 3:at + FRAME_LEN + 1])
                    if sum(nxt[:16]) & 0xFF == nxt[16]:
                        del self.buf[:at + 1]
                        continue
                self.bad += 1
                del self.buf[:at + 1]    # look for the next header one byte further on
                continue
            idx, yaw, pitch, roll, ax, ay, az, *_ = _BODY.unpack(body)
            out.append(Sample(idx, yaw / 100.0, pitch / 100.0, roll / 100.0,
                              (ax * G_PER_MG, ay * G_PER_MG, az * G_PER_MG)))
            del self.buf[:at + FRAME_LEN]


def yaw_rate(prev_deg, now_deg, dt):
    """Turn rate in rad/s between two yaws, the short way round (179 -> -179 is +2 degrees)."""
    if dt <= 0:
        return 0.0
    d = (now_deg - prev_deg + 180.0) % 360.0 - 180.0
    return math.radians(d) / dt


def quaternion(yaw_deg, pitch_deg, roll_deg):
    """(x, y, z, w) for yaw about z, then pitch about y, then roll about x (ROS order)."""
    cy, sy = math.cos(math.radians(yaw_deg) / 2), math.sin(math.radians(yaw_deg) / 2)
    cp, sp = math.cos(math.radians(pitch_deg) / 2), math.sin(math.radians(pitch_deg) / 2)
    cr, sr = math.cos(math.radians(roll_deg) / 2), math.sin(math.radians(roll_deg) / 2)
    return (sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy)


def tilt_deg(pitch_deg, roll_deg):
    """Degrees from level, from pitch and roll."""
    c = math.cos(math.radians(pitch_deg)) * math.cos(math.radians(roll_deg))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))
