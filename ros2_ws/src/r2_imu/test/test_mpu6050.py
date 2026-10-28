# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math
import struct

import pytest

from r2_imu.mpu6050 import (ACCEL_CONFIG, ACCEL_XOUT_H, CONFIG, G, GYRO_CONFIG, MPU6050,
                            PWR_MGMT_1, SMPLRT_DIV, GyroBias, parse_sample, tilt_deg)


def raw(ax=0, ay=0, az=0, t=0, gx=0, gy=0, gz=0):
    return list(struct.pack(">7h", ax, ay, az, t, gx, gy, gz))


class FakeBus:
    def __init__(self, sample=None):
        self.writes = {}
        self.sample = sample or raw()

    def write_byte_data(self, addr, reg, value):
        self.writes[reg] = value

    def read_byte_data(self, addr, reg):
        return 0x68

    def read_i2c_block_data(self, addr, reg, n):
        assert reg == ACCEL_XOUT_H and n == 14
        return self.sample


def test_level_and_still_reads_one_g_up():
    accel, gyro, _ = parse_sample(raw(az=8192), accel_g=4)
    assert accel == pytest.approx((0, 0, G))
    assert gyro == (0, 0, 0)


def test_scales_follow_the_range():
    assert parse_sample(raw(ax=16384), accel_g=2)[0][0] == pytest.approx(G)
    assert parse_sample(raw(ax=16384), accel_g=4)[0][0] == pytest.approx(2 * G)
    assert parse_sample(raw(gz=131), gyro_dps=250)[1][2] == pytest.approx(math.radians(1))
    assert parse_sample(raw(gz=-655), gyro_dps=500)[1][2] == pytest.approx(math.radians(-10))


def test_temperature():
    assert parse_sample(raw(t=0))[2] == pytest.approx(36.53)
    assert parse_sample(raw(t=-340))[2] == pytest.approx(35.53)


def test_tilt():
    assert tilt_deg((0, 0, G)) == pytest.approx(0)
    assert tilt_deg((G, 0, 0)) == pytest.approx(90)
    s = math.sin(math.radians(20)) * G
    c = math.cos(math.radians(20)) * G
    assert tilt_deg((0, s, c)) == pytest.approx(20)
    assert tilt_deg((0, 0, 0)) == 0


def test_gyro_bias_is_removed():
    b = GyroBias()
    for _ in range(10):
        b.add((0.01, -0.02, 0.005))
    assert b.remove((0.01, -0.02, 0.105)) == pytest.approx((0, 0, 0.1))


def test_no_bias_before_calibration():
    assert GyroBias().remove((0.1, 0.2, 0.3)) == (0.1, 0.2, 0.3)


def test_start_configures_the_chip():
    bus = FakeBus()
    MPU6050(bus, accel_g=4, gyro_dps=500, rate_hz=100, dlpf=3).start()
    assert bus.writes[PWR_MGMT_1] == 0x01
    assert bus.writes[CONFIG] == 3
    assert bus.writes[SMPLRT_DIV] == 9           # 1 kHz / (1 + 9) = 100 Hz
    assert bus.writes[GYRO_CONFIG] == 1 << 3
    assert bus.writes[ACCEL_CONFIG] == 1 << 3


def test_read_goes_through_the_bus():
    accel, _, _ = MPU6050(FakeBus(raw(az=8192))).read()
    assert accel[2] == pytest.approx(G)


def test_bad_settings_are_rejected():
    with pytest.raises(ValueError):
        MPU6050(FakeBus(), accel_g=3)
    with pytest.raises(ValueError):
        MPU6050(FakeBus(), gyro_dps=300)
    with pytest.raises(ValueError):
        MPU6050(FakeBus(), dlpf=0)
