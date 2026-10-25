"""R2 web console: serves the page that shows a camera, its faces and a 3D R2
whose dome turns with /dome/speed_cmd.

The page itself talks to ROS through rosbridge (ws://<pi>:9090), so this node only
serves static files: http://<pi>:8080/  (?cam=rear for another camera)
"""

import functools
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import rclpy
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node


class QuietHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        # The page changes often while the droid is being tuned: never serve a stale copy
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class WebServerNode(Node):
    def __init__(self):
        super().__init__("web_console")
        p = self.declare_parameter
        p("port", 8080)
        p("root", os.path.join(get_package_share_directory("r2_web"), "www"),
          ParameterDescriptor(description="Folder with index.html"))
        port = self.get_parameter("port").value
        root = self.get_parameter("root").value

        handler = functools.partial(QuietHandler, directory=root)
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
