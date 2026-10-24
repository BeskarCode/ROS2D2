"""MPU6050 gyro + accelerometer over I2C, without ROS.

The bus is passed in (an smbus2.SMBus on the Pi, a fake in the tests), so all of
this can be tested on a PC.

Units out: acceleration in m/s^2, rotation in rad/s, temperature in degrees C,
on the chip's own axes (the URDF says how the chip sits in the droid).
"""

import math
import struct

ADDRESS = 0x68            # 0x69 with the AD0 pin high

SMPLRT_DIV = 0x19
CONFIG = 0x1A             # digital low-pass filter
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B       # 14 bytes: accel x y z, temperature, gyro x y z (big-endian)
PWR_MGMT_1 = 0x6B
WHO_AM_I = 0x75

G = 9.80665

# Full-scale range -> (register value, LSB per unit)
ACCEL_RANGES = {2: (0, 16384.0), 4: (1, 8192.0), 8: (2, 4096.0), 16: (3, 2048.0)}        # g
GYRO_RANGES = {250: (0, 131.0), 500: (1, 65.5), 1000: (2, 32.8), 2000: (3, 16.4)}       # deg/s


def parse_sample(raw, accel_g=4, gyro_dps=500):
    """14 bytes from ACCEL_XOUT_H -> ((ax, ay, az) m/s^2, (gx, gy, gz) rad/s, temp C)."""
    ax, ay, az, t, gx, gy, gz = struct.unpack(">7h", bytes(raw))
    a_lsb = ACCEL_RANGES[accel_g][1]
    g_lsb = GYRO_RANGES[gyro_dps][1]
    accel = tuple(v / a_lsb * G for v in (ax, ay, az))
    gyro = tuple(math.radians(v / g_lsb) for v in (gx, gy, gz))
    return accel, gyro, t / 340.0 + 36.53


def tilt_deg(accel):
    """Angle between the chip's z axis and straight up, from gravity. 0 = level.

    Only meaningful while the droid is not accelerating hard.
    """
    ax, ay, az = accel
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if norm == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, az / norm))))


class GyroBias:
    """Averages the gyro while the droid stands still; a resting gyro should read 0."""

    def __init__(self):
        self.sum = [0.0, 0.0, 0.0]
        self.n = 0

    def add(self, gyro):
        for i in range(3):
            self.sum[i] += gyro[i]
        self.n += 1

    @property
    def bias(self):
        if self.n == 0:
            return (0.0, 0.0, 0.0)
        return tuple(s / self.n for s in self.sum)

    def remove(self, gyro):
        b = self.bias
        return tuple(gyro[i] - b[i] for i in range(3))


class MPU6050:
    def __init__(self, bus, address=ADDRESS, accel_g=4, gyro_dps=500, rate_hz=100, dlpf=3):
        if accel_g not in ACCEL_RANGES:
            raise ValueError(f"accel range must be one of {sorted(ACCEL_RANGES)} g")
        if gyro_dps not in GYRO_RANGES:
            raise ValueError(f"gyro range must be one of {sorted(GYRO_RANGES)} deg/s")
        if not 1 <= dlpf <= 6:
            raise ValueError("dlpf must be 1-6 (with the filter on, the chip samples at 1 kHz)")
        self.bus = bus
        self.address = address
        self.accel_g = accel_g
        self.gyro_dps = gyro_dps
        self.rate_hz = rate_hz
        self.dlpf = dlpf

    def who_am_i(self):
        """0x68 on a genuine MPU6050. Clones answer 0x70, 0x72 or 0x98 and usually work the same."""
        return self.bus.read_byte_data(self.address, WHO_AM_I)

    def start(self):
        w = self.bus.write_byte_data
        w(self.address, PWR_MGMT_1, 0x01)                     # wake up, clock from the x gyro
        w(self.address, CONFIG, self.dlpf)                    # 3 = about 44 Hz: cuts motor vibration
        w(self.address, SMPLRT_DIV, max(0, min(255, round(1000 / self.rate_hz) - 1)))
        w(self.address, GYRO_CONFIG, GYRO_RANGES[self.gyro_dps][0] << 3)
        w(self.address, ACCEL_CONFIG, ACCEL_RANGES[self.accel_g][0] << 3)

    def read(self):
        raw = self.bus.read_i2c_block_data(self.address, ACCEL_XOUT_H, 14)
        return parse_sample(raw, self.accel_g, self.gyro_dps)
