# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 IMU node for the Adafruit BNO085 in UART-RVC mode, on a Pi UART.

Topics:
  out  /imu/data    sensor_msgs/Imu    R2's attitude (fused by the chip, corrected to R2's axes), turn
                                       rate (worked out from the angles: RVC sends none), acceleration
  out  /imu/tilt    std_msgs/Float32   degrees from level
  out  /imu/status  std_msgs/String    JSON twice a second for the console (Setup → IMU)
Services (std_srvs/Trigger, the message is the console's toast):
  /imu/level_here          R2 still on a flat floor: its tilt now is 0 (saved)
  /imu/heading_zero        where R2 points now is heading 0 (until the node restarts)
  /imu/forget_calibration  drop the levelling (saved)

Settings: ~/.config/ros2d2/imu.yaml (the console writes it) wins over the package's config/imu.yaml.
in_use, port, box, front and invert_yaw change live (set_parameters) and are saved. With in_use false
the node keeps reading and reporting but publishes no /imu/data nor /imu/tilt.

The same /imu/data as r2_imu (MPU6050 + Madgwick), so whatever uses it does not care which IMU R2 has.
Heading starts at 0 where R2 points when the node starts (zero_yaw): RVC's yaw counts from power-on.
simulate:=true: no board, a pretend IMU, to try the console.
"""

import os
import time

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32, String
from std_srvs.srv import Trigger

from r2_imu_bno085.calib import Mount, check_setting, level_from, load_user, save_user
from r2_imu_bno085.imustate import Stats, sim_sample, status
from r2_imu_bno085.rvc import RvcParser, quaternion, tilt_deg, yaw_rate

# Rough noise, as variances for the message (to tune on the droid)
ORIENT_VAR = 0.01 ** 2     # rad^2
RATE_VAR = 0.02 ** 2       # (rad/s)^2, from differences of 0.01 degree steps
ACCEL_VAR = 0.05 ** 2      # (m/s^2)^2
LIVE = ("in_use", "port", "box", "front", "invert_yaw")     # the console changes these, and they are saved


def _wrap(d):
    return (d + 180.0) % 360.0 - 180.0


class Bno085Node(Node):
    def __init__(self):
        super().__init__("imu")
        p = self.declare_parameter
        p("port", "/dev/ttyAMA3", ParameterDescriptor(description="The Pi UART the BNO085's SDA (its TX) goes to"))
        p("baud", 115200)
        p("rate_hz", 100.0, ParameterDescriptor(description="Frames a second the BNO085 sends in RVC mode"))
        p("frame_id", "imu_link")
        p("zero_yaw", True, ParameterDescriptor(description="Heading 0 = where R2 points when the node starts"))
        p("invert_yaw", False, ParameterDescriptor(description="If turning left makes heading go down"))
        p("in_use", True, ParameterDescriptor(description="false: read and report, but publish no /imu/data"))
        p("box", "standing", ParameterDescriptor(description="standing (board on the floor) or lying (on the divider)"))
        p("front", "+x", ParameterDescriptor(description="Which of the board's arrows points to R2's front: +x -x +y -y"))
        p("simulate", False, ParameterDescriptor(description="No board: a pretend IMU, to try the console"))
        p("user_file", "~/.config/ros2d2/imu.yaml")
        p("tilt_warn_deg", 20.0)
        p("stale_sec", 0.5, ParameterDescriptor(description="No frame this long = warn"))
        p("reconnect_sec", 5.0)

        # the user's file wins: load it, and put its values in the parameters before anyone can change them
        self.user_file = os.path.expanduser(self.param("user_file"))
        self.cfg, self.file_error = load_user(self.user_file)
        if self.file_error:
            self.get_logger().warning(self.file_error)
        self.set_parameters([Parameter(k, value=self.cfg[k]) for k in LIVE])
        self.mount = Mount(self.cfg["level"], self.cfg["front"])
        self.add_on_set_parameters_callback(self._on_params)

        self.pub_imu = self.create_publisher(Imu, "/imu/data", 10)
        self.pub_tilt = self.create_publisher(Float32, "/imu/tilt", 10)
        self.pub_status = self.create_publisher(String, "/imu/status", 10)
        self.create_service(Trigger, "/imu/level_here", self._level_here)
        self.create_service(Trigger, "/imu/heading_zero", self._heading_zero)
        self.create_service(Trigger, "/imu/forget_calibration", self._forget)

        self.ser = None
        self.parser = RvcParser()
        self.stats = Stats()
        self.prev = None                  # (index, yaw, pitch, roll) of R2, for the rates
        self.last_chip = None             # the last frame, to keep heading continuous when the mount changes
        self.last_r2_yaw = None
        self.yaw0 = None
        self.last_at = None
        self.next_try = 0.0
        self.bad_logged = 0
        self.simulate = self.param("simulate")
        if self.simulate:
            self.sim_t0, self.sim_i = time.monotonic(), 0
            self.create_timer(0.01, self._sim_tick)
            self.get_logger().info("simulate: a pretend BNO085, no board needed")
        else:
            self.create_timer(0.005, self._tick)
        self.create_timer(0.5, self._status)

    def param(self, name):
        return self.get_parameter(name).value

    # ---- settings: checked, applied and saved ----
    def _on_params(self, params):
        changes = {}
        for prm in params:
            if prm.name in LIVE:
                why = check_setting(prm.name, prm.value)
                if why:
                    return SetParametersResult(successful=False, reason=why)
                changes[prm.name] = prm.value
        if not changes:
            return SetParametersResult(successful=True)
        new = dict(self.cfg, **changes)
        try:
            save_user(self.user_file, new)
        except OSError as e:
            return SetParametersResult(successful=False, reason=f"cannot save {self.user_file}: {e}")
        port_changed = new["port"] != self.cfg["port"]
        self.cfg = new
        self.file_error = ""
        if "front" in changes:
            self._new_mount()
        if port_changed and self.ser is not None:
            self.ser.close()
            self.ser, self.next_try = None, 0.0          # _tick opens the new port
        return SetParametersResult(successful=True)

    def _new_mount(self):
        """A new levelling or front: keep the heading where it was, and start the rates afresh."""
        old = self.mount
        self.mount = Mount(self.cfg["level"], self.cfg["front"])
        if self.last_chip is not None and self.yaw0 is not None:
            c = self.last_chip
            self.yaw0 += _wrap(self.mount.to_r2(c.yaw, c.pitch, c.roll)[0] - old.to_r2(c.yaw, c.pitch, c.roll)[0])
        self.prev = None

    # ---- services ----
    def _level_here(self, _req, res):
        lv, why = level_from(self.stats.last_second(time.monotonic()))
        if lv is None:
            res.success, res.message = False, why
            return res
        try:
            save_user(self.user_file, dict(self.cfg, level=lv))
        except OSError as e:
            res.success, res.message = False, f"cannot save {self.user_file}: {e}"
            return res
        self.cfg["level"] = lv
        self._new_mount()
        res.success = True
        res.message = f"Levelled: roll {lv['roll_deg']:.1f}°, pitch {lv['pitch_deg']:.1f}° are now 0"
        return res

    def _heading_zero(self, _req, res):
        if self.last_r2_yaw is None:
            res.success, res.message = False, "no frames from the IMU (is it connected?)"
            return res
        self.yaw0 = self.last_r2_yaw
        res.success, res.message = True, "Heading 0 is where R2 points now (until the node restarts)"
        return res

    def _forget(self, _req, res):
        try:
            save_user(self.user_file, dict(self.cfg, level=None))
        except OSError as e:
            res.success, res.message = False, f"cannot save {self.user_file}: {e}"
            return res
        self.cfg["level"] = None
        self._new_mount()
        res.success, res.message = True, "Calibration forgotten"
        return res

    # ---- the board ----
    def _open(self):
        try:
            import serial
            self.ser = serial.Serial(self.cfg["port"], self.param("baud"), timeout=0)
        except (OSError, ImportError) as e:      # serial.SerialException is an OSError
            self.get_logger().warning(f"cannot open {self.cfg['port']} ({e}); retrying every "
                                      f"{self.param('reconnect_sec')} s", throttle_duration_sec=60.0)
            return False
        self.parser = RvcParser()
        self.prev, self.yaw0, self.last_at = None, None, time.monotonic()
        self.get_logger().info(f"listening for the BNO085 on {self.cfg['port']} at {self.param('baud')} baud")
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
            self.get_logger().error(f"lost {self.cfg['port']}: {e}")
            self.ser = None
            return
        for s in self.parser.feed(data):
            self.last_at = now
            self._publish(s, now)
        if self.parser.bad > self.bad_logged:
            self.get_logger().warning(f"{self.parser.bad} frames with a wrong checksum so far "
                                      "(baud rate or wiring?)", throttle_duration_sec=10.0)
            self.bad_logged = self.parser.bad
        if now - self.last_at > self.param("stale_sec"):
            self.get_logger().warning(f"no BNO085 frames for {now - self.last_at:.1f} s "
                                      "(P0 to 3V3 for RVC mode? SDA to the Pi's RX?)", throttle_duration_sec=10.0)

    def _sim_tick(self):
        now = time.monotonic()
        self.last_at = now
        self._publish(sim_sample(now - self.sim_t0, self.sim_i), now)
        self.sim_i += 1

    def _publish(self, s, now):
        self.stats.raw(now, s.roll, s.pitch)
        self.last_chip = s
        y, pitch, roll = self.mount.to_r2(s.yaw, s.pitch, s.roll)
        self.last_r2_yaw = y
        if self.yaw0 is None:
            self.yaw0 = y if self.param("zero_yaw") else 0.0
        sign = -1.0 if self.cfg["invert_yaw"] else 1.0
        yaw = sign * _wrap(y - self.yaw0)
        accel = self.mount.vec(s.accel)
        self.stats.frame(now, pitch, roll, accel)

        msg = Imu()
        if self.prev is not None:
            # time between frames from their index (one per frame), not from when they arrived
            dt = ((s.index - self.prev[0]) % 256) / self.param("rate_hz")
            msg.angular_velocity.x = yaw_rate(self.prev[3], roll, dt)
            msg.angular_velocity.y = yaw_rate(self.prev[2], pitch, dt)
            msg.angular_velocity.z = sign * yaw_rate(self.prev[1], y, dt)
        self.prev = (s.index, y, pitch, roll)
        if not self.cfg["in_use"]:
            return

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.param("frame_id")
        o = msg.orientation
        o.x, o.y, o.z, o.w = quaternion(yaw, pitch, roll)
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = accel
        for i in (0, 4, 8):
            msg.orientation_covariance[i] = ORIENT_VAR
            msg.angular_velocity_covariance[i] = RATE_VAR
            msg.linear_acceleration_covariance[i] = ACCEL_VAR
        self.pub_imu.publish(msg)

        tilt = tilt_deg(pitch, roll)
        self.pub_tilt.publish(Float32(data=tilt))
        if tilt > self.param("tilt_warn_deg"):
            self.get_logger().warning(f"tilted {tilt:.0f} degrees", throttle_duration_sec=2.0)

    def _status(self):
        now = time.monotonic()
        age = None if self.last_at is None else now - self.last_at
        connected = age is not None and age <= self.param("stale_sec") and (self.simulate or self.ser is not None)
        self.pub_status.publish(String(data=status(
            connected=connected, port="simulated" if self.simulate else self.cfg["port"],
            fps=self.stats.fps(now), bad_frames=self.parser.bad, cfg=self.cfg, last_frame_age=age,
            bump=self.stats.bump(now), simulate=self.simulate, error=self.file_error)))


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
