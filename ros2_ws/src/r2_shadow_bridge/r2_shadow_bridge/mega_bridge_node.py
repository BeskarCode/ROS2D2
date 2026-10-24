"""R2 Mega bridge: the only node that talks to the ShadowMD Arduino Mega.

Everything else in ROS publishes what it wants; this node turns it into ShadowMD's
serial commands (see protocol.py). Safety stays on the Mega: the controller always
wins, the feet and the dome stop if the commands stop, and only the controller
(PS + L2) can switch the autonomous mode on.

Topics:
  in   /dome/speed_cmd        std_msgs/Int16      dome speed (DM: units); sent ~15 times a second
                                                  while turning and in autonomous mode; at 0 or
                                                  when it goes stale, one stop and silence
  in   /foot/cmd_vel          geometry_msgs/Twist linear.x m/s, angular.z rad/s; same rules,
                                                  converted with the calibration parameters
  in   /mega/command          std_msgs/String     MD:/S1:/S3: commands (sounds, panels, lights...)
  out  /mega/connected        std_msgs/Bool       serial port open or not
  out  /mega/log              std_msgs/String     every line the Mega prints
  out  /r2/auto_mode          std_msgs/Bool       autonomous mode on or off (latched)
  out  /r2/auto_mode/reason   std_msgs/String     why it went off: boot, button, stick,
                                                  controller, pi or disconnected (latched)
Service:
  /r2/auto_mode/disable       std_srvs/Trigger    switch the autonomous mode off
"""

import threading
import time

import rclpy
import serial
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Int16, String
from std_srvs.srv import Trigger

from r2_shadow_bridge.protocol import (command_allowed, dome_line, dome_tick, foot_tick, is_error,
                                       parse_auto_line, twist_to_units)


class MegaBridgeNode(Node):
    def __init__(self):
        super().__init__("mega_bridge")
        p = self.declare_parameter
        p("port", "/dev/r2-mega")
        p("baud", 115200)
        p("open_wait", 3.0)          # the Mega resets when the port opens
        p("reconnect_sec", 5.0)
        p("rate_hz", 15.0)           # dome and foot commands per second while fresh
        p("cmd_timeout", 0.3)        # a dome command older than this is stale
        p("max_dome_speed", 80)
        p("command_prefixes", ["MD:", "S1:", "S3:"])
        # Feet: no encoders, so these come from measuring the droid (foot_calibrate)
        p("drive_units_per_mps", 50.0)
        p("turn_units_per_radps", 30.0)
        p("max_linear", 0.4)         # m/s; the Mega has its own, harder limit
        p("max_angular", 0.6)        # rad/s
        p("foot_cmd_timeout", 0.3)

        self.ser = None
        self.lock = threading.Lock()
        self.dome_speed = 0
        self.dome_t = None           # when the last dome command arrived
        self.dome_sent_stop = True
        self.foot = (0, 0)           # Sabertooth units
        self.foot_t = None
        self.foot_sent_stop = True
        self.auto_on = False
        self.auto_reason = None

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_connected = self.create_publisher(Bool, "/mega/connected", latched)
        self.pub_log = self.create_publisher(String, "/mega/log", 50)
        self.pub_auto = self.create_publisher(Bool, "/r2/auto_mode", latched)
        self.pub_auto_reason = self.create_publisher(String, "/r2/auto_mode/reason", latched)
        self.create_subscription(Int16, "/dome/speed_cmd", self._on_dome, 10)
        self.create_subscription(Twist, "/foot/cmd_vel", self._on_foot, 10)
        self.create_subscription(String, "/mega/command", self._on_command, 10)
        self.create_service(Trigger, "/r2/auto_mode/disable", self._on_disable)
        self.create_timer(1.0 / self.get_parameter("rate_hz").value, self._tick)

        self.pub_connected.publish(Bool(data=False))
        self._set_auto(False, "boot")
        self._stop = threading.Event()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def param(self, name):
        return self.get_parameter(name).value

    # --- serial port -------------------------------------------------------------------

    def _connect(self):
        port = self.param("port")
        try:
            ser = serial.Serial(port, self.param("baud"), timeout=0.1)
        except (serial.SerialException, OSError) as e:
            self.get_logger().warn(f"no Mega on {port} ({e}); retrying every "
                                   f"{self.param('reconnect_sec')} s", throttle_duration_sec=60.0)
            return False
        self.get_logger().info(f"opened {port}; waiting {self.param('open_wait')} s for the Mega to boot")
        time.sleep(self.param("open_wait"))
        ser.reset_input_buffer()
        with self.lock:
            self.ser = ser
        self.pub_connected.publish(Bool(data=True))
        # The Mega has just restarted (the port opening resets it): the mode is off
        self._set_auto(False, "boot")
        self._write("ROS:AUTO:?\n")
        return True

    def _lost(self, why):
        with self.lock:
            if self.ser is None:
                return
            try:
                self.ser.close()
            except OSError:
                pass
            self.ser = None
        self.pub_connected.publish(Bool(data=False))
        self._set_auto(False, "disconnected")
        self.get_logger().error(f"lost the Mega: {why}")

    def _write(self, line):
        with self.lock:
            ser = self.ser
            if ser is None:
                return False
            try:
                ser.write(line.encode("ascii"))
                return True
            except (serial.SerialException, OSError) as e:
                err = e
        self._lost(err)
        return False

    def _read_loop(self):
        buf = b""
        while not self._stop.is_set():
            if self.ser is None:
                if not self._connect():
                    self._stop.wait(self.param("reconnect_sec"))
                continue
            try:
                buf += self.ser.read(256)
            except (serial.SerialException, OSError, TypeError, AttributeError) as e:
                self._lost(e)
                continue
            *lines, buf = buf.replace(b"\r", b"\n").split(b"\n")
            for raw in lines:
                line = raw.decode("ascii", "replace").strip()
                if not line:
                    continue
                self.pub_log.publish(String(data=line))
                auto = parse_auto_line(line)
                if auto is not None:
                    self._set_auto(*auto)
                elif is_error(line):
                    self.get_logger().warn(f"Mega: {line}")

    # --- commands ----------------------------------------------------------------------

    def _on_dome(self, msg):
        self.dome_speed = msg.data
        self.dome_t = time.monotonic()

    def _on_foot(self, msg):
        self.foot = twist_to_units(msg.linear.x, msg.angular.z,
                                   self.param("drive_units_per_mps"), self.param("turn_units_per_radps"),
                                   self.param("max_linear"), self.param("max_angular"))
        self.foot_t = time.monotonic()

    def _on_disable(self, request, response):
        response.success = self._write("ROS:AUTO:0\n")
        response.message = "sent ROS:AUTO:0" if response.success else "Mega not connected"
        return response

    def _set_auto(self, on, reason):
        """Publish the autonomous mode, only when it changes."""
        if (on, reason) == (self.auto_on, self.auto_reason):
            return
        changed_on = on != self.auto_on or self.auto_reason is None
        self.auto_on, self.auto_reason = on, reason
        self.pub_auto_reason.publish(String(data=reason))
        self.pub_auto.publish(Bool(data=on))
        if changed_on:
            self.get_logger().info("autonomous mode ON" if on else f"autonomous mode OFF ({reason})")

    def _on_command(self, msg):
        cmd = msg.data.strip()
        if not command_allowed(cmd, self.param("command_prefixes")):
            self.get_logger().warn(f"command not allowed: {cmd!r}")
            return
        if not self._write(cmd + "\n"):
            self.get_logger().warn(f"Mega not connected, dropped: {cmd}")

    def _tick(self):
        fresh = self.dome_t is not None and time.monotonic() - self.dome_t < self.param("cmd_timeout")
        line, self.dome_sent_stop = dome_tick(fresh and self.auto_on, self.dome_speed,
                                              self.dome_sent_stop, self.param("max_dome_speed"))
        if line:
            self._write(line)

        fresh = self.foot_t is not None and time.monotonic() - self.foot_t < self.param("foot_cmd_timeout")
        line, self.foot_sent_stop = foot_tick(fresh, self.auto_on, *self.foot, self.foot_sent_stop)
        if line:
            self._write(line)

    def destroy_node(self):
        self._write(dome_line(0, 0))
        if self.auto_on:
            self._write("ROS:FOOT:0,0\n")
        self._stop.set()
        self._reader.join(timeout=2.0)
        if self.ser is not None:
            self.ser.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = MegaBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
