# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
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
import os
import threading
import time

import rclpy
import serial
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Range
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool

from r2_pico_bridge import board_settings
from r2_pico_bridge.protocol import cfg_line, parse
from r2_sensors.config import Reloader, config_path

STATES = {"O": "ok", "N": "not_responding"}
NL = "\n"


def default_config():
    return f"{get_package_share_directory('r2_sensors')}/config/sensors.yaml"


def default_board_config():
    return f"{get_package_share_directory('r2_pico_bridge')}/config/pico_board.yaml"


class PicoBridge(Node):
    def __init__(self, **kwargs):
        super().__init__("pico_bridge", **kwargs)
        self.declare_parameter("port", "/dev/r2-pico")
        self.declare_parameter("config", "")
        self.declare_parameter("reconnect_sec", 2.0)
        self.declare_parameter("stale_sec", 3.0)
        self.declare_parameter("telemetry_timeout_sec", 5.0)
        self.declare_parameter("board_config", "")      # pico_board.yaml; "" = the user's, else the package's
        config = self.param("config") or default_config()
        self.reloader = Reloader(lambda: config_path(config))
        self.lock = threading.Lock()
        self.ser = None
        self.firmware = None
        self.proto = None
        self.commit = None
        # telemetry (TM): asked for by the console every ~2 s while its System tab shows it
        self.tm_asked_at = 0.0      # last request (monotonic), 0 = not asked
        self.tm_sent = False        # TM 1 sent on this connection
        self.telemetry = None
        self.telemetry_at = 0.0
        # the carrier board's settings (pico_board.yaml), sent as UI after every CFG
        self.board = dict(board_settings.DEFAULTS)
        self.board_seen = None      # (path, mtime) of the file last read
        self.ui_pending = False     # a UI line sent, its answer not seen yet
        self.settings_supported = None   # None = not known yet; False = old firmware (ERR unknown)
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
        self.create_subscription(Bool, "/pico/telemetry_request", self.on_telemetry_request, 10)
        self.create_subscription(String, "/pico/command", self.on_command, 10)
        # flashing: the web console asks for the port (BOOT, then it stays closed) and gives it back
        self.released = False
        self.create_service(SetBool, "/pico/release", self.on_release)
        self.reload_board()
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
        self.tm_sent = False
        self.settings_supported = None
        self.check_telemetry()
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
            self.tm_sent = False
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
            if self.released:
                self._stop.wait(0.1)
                buf = b""
                continue
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
            self.firmware, self.proto, self.commit = msg[1], msg[2], msg[3]
        elif kind == "tm":
            self.telemetry, self.telemetry_at = msg[1], time.monotonic()
        elif kind == "cfg_ok":
            self.config_error = None
            self.send_ui()
        elif kind == "ack":
            if msg[1] == "UI":
                self.ui_pending = False
                self.settings_supported = True
            if not msg[2]:
                self.get_logger().warning(f"pico: {msg[1]} ERR {msg[3]}")
        elif kind == "cfg_err":
            self.config_error = msg[1]
            self.get_logger().error(f"the Pico refused the sensors: {msg[1]}", throttle_duration_sec=60.0)
        elif kind == "err" and self.ui_pending and msg[1] == "unknown":
            self.ui_pending = False             # a firmware before 0.2.0: no UI, DISP or ID
            self.settings_supported = False
            self.get_logger().warning("the Pico firmware is too old for the board settings: update it")
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

    # --- the carrier board's settings (pico_board.yaml) and actions -------------------

    def board_path(self):
        return self.param("board_config") or board_settings.config_path(default_board_config())

    def reload_board(self):
        path = self.board_path()
        try:
            seen = (path, os.path.getmtime(path))
        except OSError:
            seen = (path, None)
        if seen == self.board_seen:
            return
        self.board_seen = seen
        if seen[1] is None:
            self.get_logger().warning(f"no {path}: the board keeps its own settings", throttle_duration_sec=60.0)
            return
        try:
            self.board = board_settings.load(path)
        except (OSError, board_settings.BoardSettingsError) as e:
            self.get_logger().error(f"pico_board.yaml: {e} (keeping the last good one)")
            return
        self.send_ui()

    def send_ui(self):
        if self.ser is None or self.settings_supported is False:
            return
        self.ui_pending = self._write(board_settings.ui_line(self.board) + NL)

    def on_command(self, msg):
        if not board_settings.command_ok(msg.data):
            self.get_logger().warning(f"/pico/command: not sent: {msg.data!r}")
            return
        if self.settings_supported is not False:
            self._write(msg.data + NL)

    def on_release(self, request, response):
        """/pico/release true: restart the Pico into its USB loader (BOOT) and leave its port
        alone, so it can be flashed. false: open it again (HELLO, CFG, UI and TM follow)."""
        if request.data:
            self.released = True
            self._write("BOOT" + NL)
            self._lost("released for flashing")
            response.message = "released"
        else:
            self.released = False
            response.message = "taken back"
        response.success = True
        return response

    # --- telemetry ------------------------------------------------------------------

    def on_telemetry_request(self, msg):
        self.tm_asked_at = time.monotonic() if msg.data else 0.0
        self.check_telemetry()

    def check_telemetry(self):
        """TM 1 while the console keeps asking, TM 0 once it stops (or says False)."""
        want = self.tm_asked_at and time.monotonic() - self.tm_asked_at < self.param("telemetry_timeout_sec")
        if want and not self.tm_sent and self.ser is not None:
            self.tm_sent = self._write("TM 1\n")
        elif not want and self.tm_sent:
            self.tm_sent = False
            self.telemetry = None           # nobody looks: no stale numbers in /pico/state
            self._write("TM 0\n")
            self.publish_state()

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
            fresh_tm = self.telemetry if time.monotonic() - self.telemetry_at < 3.0 else None
            state = {"connected": self.is_connected(), "firmware": self.firmware, "proto": self.proto,
                     "commit": self.commit, "config_error": self.config_error,
                     "sensors": dict(self.status), "telemetry": fresh_tm,
                     "settings_supported": self.settings_supported}
        text = json.dumps(state)
        if always or text != self.last_json:
            self.last_json = text
            self.pub_state.publish(String(data=text))

    def tick(self):
        self.reload()
        self.reload_board()
        self.check_telemetry()
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
