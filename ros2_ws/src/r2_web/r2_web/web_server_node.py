# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""R2 web console: serves the page that shows the cameras, their faces and a 3D R2
whose dome turns with /dome/speed_cmd, plus the camera setup page.

The pages talk to ROS through rosbridge (ws://<pi>:9090), so this node only serves files
and a small HTTP API for what ROS topics cannot do:

  GET  /api/cameras   the USB cameras plugged in (stable path, name, sizes they offer),
                      the cameras in use and the cameras.yaml text in use
  POST /api/cameras   save cameras.yaml in ~/.config/ros2d2/ (body: {"yaml": "..."});
                      it then wins over the package's file. The file stays hand-editable.
  GET  /api/sensors   sensors.yaml in use: its text, the sensors, any error in it, and
                      whether the lidar is plugged in (/dev/r2-lidar)
  POST /api/sensors   save sensors.yaml in ~/.config/ros2d2/ (body: {"yaml": "..."}), only if
                      it is valid; the sensors' poses follow at once (sensor_tf reloads it)
  GET  /api/nav       nav.yaml in use (the navigator's settings) and any error in it
  POST /api/nav       save nav.yaml in ~/.config/ros2d2/ (body: {"yaml": "..."}), only if valid
  POST /api/restart   restart ROS2D2 (systemd unit r2d2) so a new camera list is used

http://<pi>:8080/          console        http://<pi>:8080/setup.html   camera and sensor setup
"""

import functools
import glob
import json
import os
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node

from r2_camera.config import USER_CONFIG, config_path, load_cameras, usb_cameras
from r2_camera.source import list_modes
from r2_sensors.config import USER_CONFIG as SENSORS_USER_CONFIG
from r2_nav.nav_core import USER_CONFIG as NAV_USER_CONFIG
from r2_web.nav_api import nav_payload, save_nav
from r2_web.sensors_api import save_sensors, sensors_payload

SERVICE = "r2d2"


def camera_name(path):
    """What the camera calls itself (from sysfs), e.g. 'Innomaker-U20CAM-720P'."""
    dev = os.path.basename(os.path.realpath(path))
    try:
        with open(f"/sys/class/video4linux/{dev}/name", encoding="utf-8") as f:
            return f.read().split(":")[0].strip()
    except OSError:
        return dev


def detected_cameras():
    out = []
    by_id = {os.path.realpath(p): p for p in glob.glob("/dev/v4l/by-id/*video-index0")}
    for path in usb_cameras():
        dev = os.path.realpath(path)
        out.append({
            "path": path,                    # stable by USB port
            "id": by_id.get(dev, ""),        # stable by camera model/serial
            "device": dev,
            "name": camera_name(path),
            "modes": list_modes(dev, "MJPG"),
        })
    return out


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}
    default_config = ""
    sensors_default = ""
    nav_default = ""

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        # The pages change often while the droid is being tuned: never serve a stale copy
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/nav":
            return self._json(200, nav_payload(self.nav_default, NAV_USER_CONFIG))
        if self.path.split("?")[0] == "/api/sensors":
            return self._json(200, sensors_payload(self.sensors_default, SENSORS_USER_CONFIG))
        if self.path.split("?")[0] != "/api/cameras":
            return super().do_GET()
        path = config_path(self.default_config)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            cameras = load_cameras(path)
        except (OSError, yaml.YAMLError) as e:
            return self._json(500, {"error": str(e)})
        self._json(200, {"file": path, "saved": path == USER_CONFIG, "yaml": text,
                         "cameras": cameras, "detected": detected_cameras()})

    def do_POST(self):
        route = self.path.split("?")[0]
        if route == "/api/restart":
            # Answer first: restarting stops this very server
            self._json(200, {"ok": True})
            threading.Timer(0.5, lambda: subprocess.run(
                ["sudo", "-n", "systemctl", "restart", SERVICE], check=False)).start()
            return
        if route == "/api/nav":
            try:
                text = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["yaml"]
            except (ValueError, KeyError, TypeError) as e:
                return self._json(400, {"error": f"not saved: {e}"})
            return self._json(*save_nav(text, NAV_USER_CONFIG))
        if route == "/api/sensors":
            try:
                text = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["yaml"]
            except (ValueError, KeyError, TypeError) as e:
                return self._json(400, {"error": f"not saved: {e}"})
            return self._json(*save_sensors(text, SENSORS_USER_CONFIG))
        if route != "/api/cameras":
            return self._json(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            text = body["yaml"]
            parsed = yaml.safe_load(text) or {}
            if not isinstance(parsed, dict):
                raise ValueError("cameras.yaml must be a list of cameras (name: settings) or auto:")
        except (ValueError, KeyError, yaml.YAMLError) as e:
            return self._json(400, {"error": f"not saved: {e}"})
        os.makedirs(os.path.dirname(USER_CONFIG), exist_ok=True)
        with open(USER_CONFIG, "w", encoding="utf-8") as f:
            f.write(text if text.endswith("\n") else text + "\n")
        self._json(200, {"ok": True, "file": USER_CONFIG})


class WebServerNode(Node):
    def __init__(self):
        super().__init__("web_console")
        p = self.declare_parameter
        p("port", 8080)
        p("root", os.path.join(get_package_share_directory("r2_web"), "www"),
          ParameterDescriptor(description="Folder with index.html"))
        port = self.get_parameter("port").value
        root = self.get_parameter("root").value

        Handler.default_config = os.path.join(get_package_share_directory("r2_camera"), "config", "cameras.yaml")
        Handler.sensors_default = os.path.join(get_package_share_directory("r2_sensors"), "config", "sensors.yaml")
        Handler.nav_default = os.path.join(get_package_share_directory("r2_nav"), "config", "nav.yaml")
        handler = functools.partial(Handler, directory=root)
        self.httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.get_logger().info(f"Web console on http://<this machine>:{port}/ (serving {root})")

    def destroy_node(self):
        self.httpd.shutdown()
        super().destroy_node()


def main():
    rclpy.init()
    node = WebServerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
