# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Is rosbridge still passing messages? rosbridge can stay alive but stop sending anything (its
executor thread dies on an rclpy race when a page closes: "InvalidHandle: cannot use Destroyable
because destruction was requested"), and then every page shows the Pico, the Mega... as gone.
probe() connects like a browser, subscribes to a topic that is published every second and says
whether a message came. A bare WebSocket client (the Pi has no websocket library): only what
this needs, unit-tested on the frame format."""
import base64
import json
import os
import socket
import struct
import time


def frame(text):
    """A client text frame: FIN + text opcode, masked as clients must."""
    data = text.encode("utf-8")
    head = bytearray([0x81])
    n = len(data)
    if n < 126:
        head.append(0x80 | n)
    elif n < 65536:
        head += bytes([0x80 | 126]) + struct.pack("!H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack("!Q", n)
    mask = os.urandom(4)
    return bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def read_frame(recv):
    """One server frame from recv(n) (returns exactly n bytes or raises): (opcode, payload)."""
    b0, b1 = recv(2)
    n = b1 & 0x7F
    if n == 126:
        n = struct.unpack("!H", recv(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", recv(8))[0]
    mask = recv(4) if b1 & 0x80 else None
    data = recv(n) if n else b""
    if mask:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return b0 & 0x0F, data


def probe(topic, msg_type, host="127.0.0.1", port=9090, wait=4.0):
    """True when rosbridge sends a message of `topic` within `wait` seconds."""
    deadline = time.monotonic() + wait
    with socket.create_connection((host, port), timeout=wait) as s:
        key = base64.b64encode(os.urandom(16)).decode()
        s.sendall((f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(1024)
            if not chunk:
                return False
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            return False
        rest = bytearray(head.split(b"\r\n\r\n", 1)[1])

        def recv(n):
            while len(rest) < n:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise TimeoutError
                s.settimeout(left)
                chunk = s.recv(4096)
                if not chunk:
                    raise ConnectionError("closed")
                rest.extend(chunk)
            out = bytes(rest[:n])
            del rest[:n]
            return out

        s.sendall(frame(json.dumps({"op": "subscribe", "topic": topic, "type": msg_type})))
        try:
            while time.monotonic() < deadline:
                op, data = read_frame(recv)
                if op == 1 and json.loads(data.decode("utf-8", "replace")).get("topic") == topic:
                    return True
                if op == 8:
                    return False
        except (TimeoutError, socket.timeout, ConnectionError, ValueError):
            return False
    return False
