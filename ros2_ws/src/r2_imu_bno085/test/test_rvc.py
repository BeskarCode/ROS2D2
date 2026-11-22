# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import math
import struct

import pytest

from r2_imu_bno085.rvc import FRAME_LEN, G_PER_MG, RvcParser, frame_bytes, quaternion, tilt_deg, yaw_rate


def frame(index=0, yaw=0.0, pitch=0.0, roll=0.0, ax=0, ay=0, az=1000, bad_sum=False):
    """A UART-RVC frame as the BNO085 sends it: angles in 0.01 degree, acceleration in mg."""
    data = frame_bytes(index, yaw, pitch, roll, ax, ay, az)
    if bad_sum:
        data = data[:-1] + bytes([(data[-1] + 1) & 0xFF])
    return data


def test_a_frame_is_19_bytes_header_body_checksum():
    f = frame(index=7, yaw=12.34, pitch=-1.5, roll=0.25, ax=10, ay=-20, az=980)
    assert len(f) == FRAME_LEN == 19
    assert f[:2] == b"\xaa\xaa"
    body = f[2:]
    assert sum(body[:16]) & 0xFF == body[16]
    idx, yaw, pitch, roll, ax, ay, az = struct.unpack("<Bhhhhhh", body[:13])
    assert (idx, yaw, pitch, roll, ax, ay, az) == (7, 1234, -150, 25, 10, -20, 980)


def test_reads_angles_in_degrees_and_acceleration_in_m_s2():
    p = RvcParser()
    out = p.feed(frame(index=3, yaw=90.0, pitch=-10.0, roll=5.0, ax=0, ay=0, az=1000))
    assert len(out) == 1
    s = out[0]
    assert s.index == 3
    assert (s.yaw, s.pitch, s.roll) == pytest.approx((90.0, -10.0, 5.0))
    assert s.accel == pytest.approx((0.0, 0.0, 1000 * G_PER_MG))
    assert s.accel[2] == pytest.approx(9.80665, abs=1e-3)


def test_frames_split_across_reads_and_noise_before_the_header():
    p = RvcParser()
    data = b"\x01\x02\xaa" + frame(index=1, yaw=1.0) + frame(index=2, yaw=2.0)
    got = []
    for i in range(0, len(data), 5):                # the serial port hands out bits and pieces
        got += p.feed(data[i:i + 5])
    assert [s.index for s in got] == [1, 2]
    assert p.bad == 0


def test_a_bad_checksum_is_dropped_and_counted_and_the_next_frame_still_reads():
    p = RvcParser()
    got = p.feed(frame(index=1, bad_sum=True) + frame(index=2, yaw=45.0))
    assert [s.index for s in got] == [2]
    assert p.bad == 1


def test_an_aa_inside_a_bad_frame_does_not_lose_the_next_one():
    p = RvcParser()
    # 0xAA 0xAA inside the body (yaw = 0xAAAA): a frame only counts if its checksum agrees
    tricky = frame(index=0xAA, yaw=struct.unpack("<h", b"\xaa\xaa")[0] / 100.0, bad_sum=True)
    got = p.feed(tricky + frame(index=9, yaw=10.0))
    assert [s.index for s in got] == [9]


def test_yaw_rate_takes_the_short_way_across_plus_minus_180():
    assert yaw_rate(179.0, -179.0, 0.01) == pytest.approx(math.radians(2.0) / 0.01)
    assert yaw_rate(-179.0, 179.0, 0.01) == pytest.approx(-math.radians(2.0) / 0.01)
    assert yaw_rate(10.0, 10.5, 0.01) == pytest.approx(math.radians(0.5) / 0.01)
    assert yaw_rate(10.0, 11.0, 0.0) == 0.0          # no time between them: no rate


def test_quaternion_from_yaw_pitch_roll():
    assert quaternion(0, 0, 0) == pytest.approx((0.0, 0.0, 0.0, 1.0))           # x, y, z, w
    x, y, z, w = quaternion(90.0, 0, 0)
    assert (x, y, z, w) == pytest.approx((0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4)))
    q = quaternion(30.0, 20.0, -10.0)
    assert sum(c * c for c in q) == pytest.approx(1.0)


def test_tilt_from_pitch_and_roll():
    assert tilt_deg(0, 0) == pytest.approx(0.0)
    assert tilt_deg(10.0, 0) == pytest.approx(10.0)
    assert tilt_deg(0, -15.0) == pytest.approx(15.0)
    assert tilt_deg(10.0, 10.0) > 10.0


def test_index_0xaa_is_a_real_frame_not_a_stray_byte():
    p = RvcParser()
    got = p.feed(frame(index=0xAA, yaw=3.0) + frame(index=0xAB, yaw=4.0))
    assert [s.index for s in got] == [0xAA, 0xAB]
    assert p.bad == 0


def test_the_example_frame_of_the_ceva_datasheet():
    # BNO08X datasheet 1000-3927 v1.17, section 1.2.5.2
    msg = bytes.fromhex("AAAADE01009 2FF25088DFEECFFD103000000E7".replace(" ", ""))
    got = RvcParser().feed(msg)
    assert len(got) == 1
    s = got[0]
    assert s.index == 222
    assert (s.yaw, s.pitch, s.roll) == pytest.approx((0.01, -1.10, 20.85))
    assert s.accel == pytest.approx((-3.638, -0.196, 9.581), abs=1e-3)
    assert frame_bytes(222, 0.01, -1.10, 20.85, -371, -20, 977) == msg
