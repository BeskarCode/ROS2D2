# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""A fake smbus2 with a pretend MPU6050, for the test bench (no I2C on a PC).

    PYTHONPATH=/r2/docker/fakes ros2 launch r2_imu imu.launch.py

The pretend droid stands level and still for the first 3 seconds (the gyro
calibration), then turns on the spot at FAKE_YAW_DPS degrees per second. The
gyro always carries a small fixed offset, like a real one, that the node must remove.
"""

import os
import struct
import time

YAW_DPS = float(os.environ.get("FAKE_YAW_DPS", "10"))
STILL_SEC = 3.0
OFFSET_LSB = (40, -25, 30)      # resting gyro offset, at 65.5 LSB per deg/s (+-500)
ACCEL_1G = 8192                 # +-4 g


class SMBus:
    def __init__(self, bus):
        self.t0 = time.monotonic()

    def write_byte_data(self, addr, reg, value):
        pass

    def read_byte_data(self, addr, reg):
        return 0x68

    def read_i2c_block_data(self, addr, reg, n):
        turning = time.monotonic() - self.t0 > STILL_SEC
        gz = round(YAW_DPS * 65.5) if turning else 0
        gx, gy, gz = OFFSET_LSB[0], OFFSET_LSB[1], OFFSET_LSB[2] + gz
        return list(struct.pack(">7h", 0, 0, ACCEL_1G, 0, gx, gy, gz))
