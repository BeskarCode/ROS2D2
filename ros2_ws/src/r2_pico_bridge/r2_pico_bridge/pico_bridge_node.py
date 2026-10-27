"""Bridge to the Pico that reads the distance sensors (VL53L0X, HC-SR04).

  in   sensors.yaml                  the Pico's sensors and pins (reloaded when saved)
  out  /range/<name>  sensor_msgs/Range   each sensor that answers; inf = nothing in range
                                     (only the Pico's -1; any other negative is a glitch: dropped).
                                     Closer than range_min is sent as range_min: the navigator
                                     reads anything out of [min, max] as "nothing there".
                                     One that does not answer publishes nothing, so whoever
                                     listens sees it go quiet (never "the way is clear").
  out  /pico/connected  std_msgs/Bool     latched
  out  /pico/state      std_msgs/String   JSON, every second and on change:
       {"connected", "firmware", "config_error", "sensors": {name: ok|not_responding|waiting}}

Parameters: port (/dev/r2-pico), config (the r2_sensors package's sensors.yaml; the one
saved from the web console wins), reconnect_sec, stale_sec (no HB for this long = not
connected). The protocol is in protocol.py.
"""

import json
import math
import threading
import time

import rclpy
import serial
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Range
from std_msgs.msg import Bool, String

from r2_pico_bridge.protocol import cfg_line, parse
from r2_sensors.config import Reloader, config_path

STATES = {"O": "ok", "N": "not_responding"}


def default_config():
    return f"{get_package_share_directory('r2_sensors')}/config/sensors.yaml"


class PicoBridge(Node):
    def __init__(self, **kwargs):
        super().__init__("pico_bridge", **kwargs)
        self.declare_parameter("port", "/dev/r2-pico")
        self.declare_parameter("config", "")
        self.declare_parameter("reconnect_sec", 2.0)
        self.declare_parameter("stale_sec", 3.0)
        config = self.param("config") or default_config()
        self.reloader = Reloader(lambda: config_path(config))
        self.lock = threading.Lock()
        self.ser = None
        self.firmware = None
        self.config_error = None
        self.last_hb = 0.0
        self.sensors = {}           # name -> settings, as last sent to the Pico
        self.names = []             # the Pico's index -> name
        self.line = "CFG\n"
        self.status = {}            # name -> ok | not_responding | waiting
        self.connected = None
        self.last_json = None
        self.pub_range = {}
        self.pub_state = self.create_publisher(String, "/pico/state", 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_connected = self.create_publisher(Bool, "/pico/connected", latched)
        self.reload(force=True)
        self.create_timer(1.0, self.tick)
        self.create_timer(0.2, self.check_connected)
        self._stop = threading.Event()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def param(self, name):
        return self.get_parameter(name).value

    # --- sensors.yaml ---------------------------------------------------------------

    def reload(self, force=False):
        sensors = self.reloader.poll()
        if self.reloader.error and sensors is None:
            self.get_logger().error(f"sensors.yaml: {self.reloader.error} (keeping the last good one)",
                                    throttle_duration_sec=60.0)
        if sensors is None and not force:
            return
        line, names = cfg_line(self.reloader.sensors)
        if line == self.line and not force:
            return
        with self.lock:
            self.line, self.names = line, names
            self.sensors = {n: self.reloader.sensors[n] for n in names}
            self.status = {n: "waiting" for n in names}
        for n in names:
            if n not in self.pub_range:
                self.pub_range[n] = self.create_publisher(Range, f"/range/{n}", qos_profile_sensor_data)
        self.send_cfg()
        self.publish_state()

    def send_cfg(self):
        self._write(self.line)

    # --- serial port ----------------------------------------------------------------

    def _connect(self):
        port = self.param("port")
        try:
            ser = serial.Serial(port, 115200, timeout=0.1)
        except (serial.SerialException, OSError) as e:
            self.get_logger().warning(f"no Pico on {port} ({e}); retrying", throttle_duration_sec=60.0)
            return False
        self.get_logger().info(f"opened {port}")
        with self.lock:
            self.ser = ser
            self.status = {n: "waiting" for n in self.names}
        self._write("HELLO\n")
        self.send_cfg()
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
            self.last_hb = 0.0
        self.get_logger().error(f"lost the Pico: {why}")

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
                buf = b""
                continue
            try:
                data = self.ser.read(256)
            except (serial.SerialException, OSError, TypeError, AttributeError) as e:
                self._lost(e)
                continue
            buf += data
            *lines, buf = buf.replace(b"\r", b"").split(b"\n")
            for raw in lines:
                self.on_line(raw.decode("ascii", "replace").strip())

    # --- what the Pico says ---------------------------------------------------------

    def on_line(self, line):
        msg = parse(line)
        if msg is None:
            if line:
                self.get_logger().debug(f"pico: {line}")
            return
        kind = msg[0]
        if kind == "hello":
            self.firmware = msg[1]
        elif kind == "cfg_ok":
            self.config_error = None
        elif kind == "cfg_err":
            self.config_error = msg[1]
            self.get_logger().error(f"the Pico refused the sensors: {msg[1]}", throttle_duration_sec=60.0)
        elif kind == "err":
            self.get_logger().warning(f"pico: ERR {msg[1]}")
        elif kind == "hb":
            self.on_heartbeat(msg[2])
        elif kind == "r":
            self.on_readings(msg[1])
        if kind != "r":
            self.publish_state()

    def on_heartbeat(self, states):
        resend = False
        with self.lock:
            self.last_hb = time.monotonic()
            if states is None or len(states) != len(self.names):
                # Restarted, or still on an older CFG. After a CFG ERR it stays without
                # sensors: sending the same one again would only be refused again.
                resend = self.config_error is None
            else:
                self.status = {n: STATES[c] for n, c in zip(self.names, states)}
        if resend:
            self.send_cfg()

    def on_readings(self, items):
        stamp = self.get_clock().now().to_msg()
        with self.lock:
            names, status, sensors = self.names, self.status, self.sensors
        for i, mm in items:
            if i >= len(names) or status.get(names[i]) != "ok" or mm < -1:
                continue
            name = names[i]
            s = sensors[name]
            m = Range()
            m.header.stamp = stamp
            m.header.frame_id = f"{name}_link"
            m.radiation_type = Range.ULTRASOUND if s["type"] == "hcsr04" else Range.INFRARED
            m.field_of_view = math.radians(s["fov_deg"])
            m.min_range = float(s["range_min"])
            m.max_range = float(s["range_max"])
            m.range = math.inf if mm == -1 else max(mm / 1000.0, m.min_range)
            self.pub_range[name].publish(m)

    # --- state ----------------------------------------------------------------------

    def is_connected(self):
        return self.ser is not None and time.monotonic() - self.last_hb < self.param("stale_sec")

    def check_connected(self):
        connected = self.is_connected()
        if connected != self.connected:
            self.connected = connected
            self.pub_connected.publish(Bool(data=connected))
            self.publish_state()

    def publish_state(self, always=False):
        with self.lock:
            state = {"connected": self.is_connected(), "firmware": self.firmware,
                     "config_error": self.config_error, "sensors": dict(self.status)}
        text = json.dumps(state)
        if always or text != self.last_json:
            self.last_json = text
            self.pub_state.publish(String(data=text))

    def tick(self):
        self.reload()
        self.publish_state(always=True)

    def destroy_node(self):
        self._stop.set()
        self._reader.join(timeout=2)
        with self.lock:
            if self.ser is not None:
                self.ser.close()
                self.ser = None
        return super().destroy_node()


def main():
    rclpy.init()
    node = PicoBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
