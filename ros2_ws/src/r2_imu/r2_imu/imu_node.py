"""R2 IMU node: the MPU6050 (gyro + accelerometer) on the Pi's I2C bus.

Topics:
  out  /imu/data_raw     sensor_msgs/Imu          rotation and acceleration, no orientation
                                                  (imu_filter_madgwick adds it -> /imu/data)
  out  /imu/tilt         std_msgs/Float32         degrees from level, from gravity
  out  /imu/temperature  sensor_msgs/Temperature  chip temperature, once a second

At start the droid must stand still for `calibrate_sec`: the gyro's resting
offset is measured and removed from then on.
"""

import time

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from sensor_msgs.msg import Imu, Temperature
from std_msgs.msg import Float32

from r2_imu.mpu6050 import MPU6050, GyroBias, tilt_deg

# Rough noise of an MPU6050 at these settings, as variances for the message
GYRO_VAR = 0.005 ** 2      # (rad/s)^2
ACCEL_VAR = 0.04 ** 2      # (m/s^2)^2


class ImuNode(Node):
    def __init__(self):
        super().__init__("imu")
        p = self.declare_parameter
        p("bus", 1, ParameterDescriptor(description="I2C bus number; 1 = Pi header pins 3 and 5"))
        p("address", 0x68, ParameterDescriptor(description="0x68, or 0x69 with AD0 high"))
        p("rate_hz", 100.0)
        p("accel_range_g", 4)
        p("gyro_range_dps", 500)
        p("dlpf", 3, ParameterDescriptor(description="Low-pass filter 1-6; 3 = about 44 Hz"))
        p("frame_id", "imu_link")
        p("calibrate_sec", 2.0, ParameterDescriptor(description="Stand still this long at start"))
        p("tilt_warn_deg", 20.0)
        p("reconnect_sec", 5.0)

        self.pub_imu = self.create_publisher(Imu, "/imu/data_raw", 10)
        self.pub_tilt = self.create_publisher(Float32, "/imu/tilt", 10)
        self.pub_temp = self.create_publisher(Temperature, "/imu/temperature", 10)

        self.chip = None
        self.bias = GyroBias()
        self.calibrated = False
        self.calib_until = None
        self.next_try = 0.0
        self.last_temp = 0.0
        self.create_timer(1.0 / self.param("rate_hz"), self._tick)

    def param(self, name):
        return self.get_parameter(name).value

    def _open(self):
        try:
            from smbus2 import SMBus
            bus = SMBus(self.param("bus"))
            chip = MPU6050(bus, self.param("address"), self.param("accel_range_g"),
                           self.param("gyro_range_dps"), self.param("rate_hz"), self.param("dlpf"))
            who = chip.who_am_i()
            if who != 0x68:
                self.get_logger().warning(f"WHO_AM_I is 0x{who:02x}, not 0x68: probably a clone, trying anyway")
            chip.start()
        except (OSError, ImportError) as e:
            self.get_logger().warning(f"no MPU6050 on bus {self.param('bus')} at 0x{self.param('address'):02x} "
                                   f"({e}); retrying every {self.param('reconnect_sec')} s",
                                   throttle_duration_sec=60.0)
            return False
        self.chip = chip
        self.bias = GyroBias()
        self.calibrated = False
        self.calib_until = time.monotonic() + self.param("calibrate_sec")
        self.get_logger().info(f"MPU6050 found; keep the droid still for {self.param('calibrate_sec')} s")
        return True

    def _tick(self):
        now = time.monotonic()
        if self.chip is None:
            if now >= self.next_try and not self._open():
                self.next_try = now + self.param("reconnect_sec")
            return
        try:
            accel, gyro, temp = self.chip.read()
        except OSError as e:
            self.get_logger().error(f"lost the MPU6050: {e}")
            self.chip = None
            return

        if not self.calibrated:
            self.bias.add(gyro)
            if now < self.calib_until:
                return
            self.calibrated = True
            b = self.bias.bias
            self.get_logger().info(f"gyro offset {b[0]:+.4f} {b[1]:+.4f} {b[2]:+.4f} rad/s; publishing")

        stamp = self.get_clock().now().to_msg()
        gx, gy, gz = self.bias.remove(gyro)
        msg = Imu()
        msg.header.stamp = stamp
        msg.header.frame_id = self.param("frame_id")
        msg.orientation_covariance[0] = -1.0        # no orientation here; the filter adds it
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = gx, gy, gz
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = accel
        for i in (0, 4, 8):
            msg.angular_velocity_covariance[i] = GYRO_VAR
            msg.linear_acceleration_covariance[i] = ACCEL_VAR
        self.pub_imu.publish(msg)

        tilt = tilt_deg(accel)
        self.pub_tilt.publish(Float32(data=tilt))
        if tilt > self.param("tilt_warn_deg"):
            self.get_logger().warning(f"tilted {tilt:.0f} degrees", throttle_duration_sec=2.0)

        if now - self.last_temp >= 1.0:
            self.last_temp = now
            t = Temperature()
            t.header.stamp = stamp
            t.header.frame_id = self.param("frame_id")
            t.temperature = temp
            self.pub_temp.publish(t)


def main():
    rclpy.init()
    node = ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
