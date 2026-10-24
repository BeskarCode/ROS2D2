"""R2 Mega bridge: the only node that talks to the ShadowMD Arduino Mega.

Everything else in ROS publishes what it wants; this node turns it into ShadowMD's
serial commands (see protocol.py). Safety stays on the Mega: the controller always
wins, and the dome stops if the commands stop.

Topics:
  in   /dome/speed_cmd   std_msgs/Int16   dome speed (DM: units); sent ~15 times a second
                                          while turning; at 0 or when it goes stale,
                                          one DM:0 and silence
  in   /mega/command     std_msgs/String  MD:/S1:/S3: commands (sounds, panels, lights...)
  out  /mega/connected   std_msgs/Bool    serial port open or not
  out  /mega/log         std_msgs/String  every line the Mega prints
"""

import threading
import time

import rclpy
import serial
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, Int16, String

from r2_shadow_bridge.protocol import command_allowed, dome_line, dome_tick, is_error


class MegaBridgeNode(Node):
    def __init__(self):
        super().__init__("mega_bridge")
        p = self.declare_parameter
        p("port", "/dev/r2-mega")
        p("baud", 115200)
        p("open_wait", 3.0)          # the Mega resets when the port opens
        p("reconnect_sec", 5.0)
        p("rate_hz", 15.0)           # DM: per second while the dome command is fresh
        p("cmd_timeout", 0.3)        # a dome command older than this is stale
        p("max_dome_speed", 80)
        p("command_prefixes", ["MD:", "S1:", "S3:"])

        self.ser = None
        self.lock = threading.Lock()
        self.dome_speed = 0
        self.dome_t = None           # when the last dome command arrived
        self.dome_sent_stop = True

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_connected = self.create_publisher(Bool, "/mega/connected", latched)
        self.pub_log = self.create_publisher(String, "/mega/log", 50)
        self.create_subscription(Int16, "/dome/speed_cmd", self._on_dome, 10)
        self.create_subscription(String, "/mega/command", self._on_command, 10)
        self.create_timer(1.0 / self.get_parameter("rate_hz").value, self._tick)

        self.pub_connected.publish(Bool(data=False))
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
                if is_error(line):
                    self.get_logger().warn(f"Mega: {line}")

    # --- commands ----------------------------------------------------------------------

    def _on_dome(self, msg):
        self.dome_speed = msg.data
        self.dome_t = time.monotonic()

    def _on_command(self, msg):
        cmd = msg.data.strip()
        if not command_allowed(cmd, self.param("command_prefixes")):
            self.get_logger().warn(f"command not allowed: {cmd!r}")
            return
        if not self._write(cmd + "\n"):
            self.get_logger().warn(f"Mega not connected, dropped: {cmd}")

    def _tick(self):
        fresh = self.dome_t is not None and time.monotonic() - self.dome_t < self.param("cmd_timeout")
        line, self.dome_sent_stop = dome_tick(fresh, self.dome_speed, self.dome_sent_stop,
                                              self.param("max_dome_speed"))
        if line:
            self._write(line)

    def destroy_node(self):
        self._write(dome_line(0, 0))
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
