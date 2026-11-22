# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 IMU node for the Adafruit BNO085 in UART-RVC mode, on a Pi UART.

Topics:
  out  /imu/data   sensor_msgs/Imu    orientation (fused by the chip), turn rate (worked out from
                                      the angles: RVC sends none) and acceleration
  out  /imu/tilt   std_msgs/Float32   degrees from level

The same /imu/data as r2_imu (MPU6050 + Madgwick), so whatever uses it does not care which IMU
R2 has. Yaw starts at 0 where R2 points when the node starts (zero_yaw).
"""

import time

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32

from r2_imu_bno085.rvc import RvcParser, quaternion, tilt_deg, yaw_rate

# Rough noise, as variances for the message (to tune on the droid)
ORIENT_VAR = 0.01 ** 2     # rad^2
RATE_VAR = 0.02 ** 2       # (rad/s)^2, from differences of 0.01 degree steps
ACCEL_VAR = 0.05 ** 2      # (m/s^2)^2


class Bno085Node(Node):
    def __init__(self):
        super().__init__("imu")
        p = self.declare_parameter
        p("port", "/dev/ttyAMA3", ParameterDescriptor(description="The Pi UART the BNO085's SDA (its TX) goes to"))
        p("baud", 115200)
        p("rate_hz", 100.0, ParameterDescriptor(description="Frames a second the BNO085 sends in RVC mode"))
        p("frame_id", "imu_link")
        p("zero_yaw", True, ParameterDescriptor(description="Yaw 0 = where R2 points when the node starts"))
        p("invert_yaw", False, ParameterDescriptor(description="If turning left makes yaw go down"))
        p("tilt_warn_deg", 20.0)
        p("stale_sec", 0.5, ParameterDescriptor(description="No frame this long = warn"))
        p("reconnect_sec", 5.0)

        self.pub_imu = self.create_publisher(Imu, "/imu/data", 10)
        self.pub_tilt = self.create_publisher(Float32, "/imu/tilt", 10)

        self.ser = None
        self.parser = RvcParser()
        self.prev = None                  # last Sample, for the rates
        self.yaw0 = None
        self.last_at = None
        self.next_try = 0.0
        self.bad_logged = 0
        self.create_timer(0.005, self._tick)

    def param(self, name):
        return self.get_parameter(name).value

    def _open(self):
        try:
            import serial
            self.ser = serial.Serial(self.param("port"), self.param("baud"), timeout=0)
        except (OSError, ImportError) as e:      # serial.SerialException is an OSError
            self.get_logger().warning(f"cannot open {self.param('port')} ({e}); retrying every "
                                      f"{self.param('reconnect_sec')} s", throttle_duration_sec=60.0)
            return False
        self.parser = RvcParser()
        self.prev, self.yaw0, self.last_at = None, None, time.monotonic()
        self.get_logger().info(f"listening for the BNO085 on {self.param('port')} at {self.param('baud')} baud")
        return True

    def _tick(self):
        now = time.monotonic()
        if self.ser is None:
            if now >= self.next_try and not self._open():
                self.next_try = now + self.param("reconnect_sec")
            return
        try:
            data = self.ser.read(self.ser.in_waiting or 1)
        except OSError as e:
            self.get_logger().error(f"lost {self.param('port')}: {e}")
            self.ser = None
            return
        for s in self.parser.feed(data):
            self.last_at = now
            self._publish(s)
        if self.parser.bad > self.bad_logged:
            self.get_logger().warning(f"{self.parser.bad} frames with a wrong checksum so far "
                                      "(baud rate or wiring?)", throttle_duration_sec=10.0)
            self.bad_logged = self.parser.bad
        if now - self.last_at > self.param("stale_sec"):
            self.get_logger().warning(f"no BNO085 frames for {now - self.last_at:.1f} s "
                                      "(P0 to 3V3 for RVC mode? SDA to the Pi's RX?)", throttle_duration_sec=10.0)

    def _publish(self, s):
        sign = -1.0 if self.param("invert_yaw") else 1.0
        if self.yaw0 is None:
            self.yaw0 = s.yaw if self.param("zero_yaw") else 0.0
        yaw = sign * (((s.yaw - self.yaw0) + 180.0) % 360.0 - 180.0)

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.param("frame_id")
        o = msg.orientation
        o.x, o.y, o.z, o.w = quaternion(yaw, s.pitch, s.roll)
        if self.prev is not None:
            # time between frames from their index (one per frame), not from when they arrived
            dt = ((s.index - self.prev.index) % 256) / self.param("rate_hz")
            msg.angular_velocity.x = yaw_rate(self.prev.roll, s.roll, dt)
            msg.angular_velocity.y = yaw_rate(self.prev.pitch, s.pitch, dt)
            msg.angular_velocity.z = sign * yaw_rate(self.prev.yaw, s.yaw, dt)
        self.prev = s
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = s.accel
        for i in (0, 4, 8):
            msg.orientation_covariance[i] = ORIENT_VAR
            msg.angular_velocity_covariance[i] = RATE_VAR
            msg.linear_acceleration_covariance[i] = ACCEL_VAR
        self.pub_imu.publish(msg)

        tilt = tilt_deg(s.pitch, s.roll)
        self.pub_tilt.publish(Float32(data=tilt))
        if tilt > self.param("tilt_warn_deg"):
            self.get_logger().warning(f"tilted {tilt:.0f} degrees", throttle_duration_sec=2.0)


def main():
    rclpy.init()
    node = Bno085Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
