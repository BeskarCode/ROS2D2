# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import json
import socket
import struct
import threading

from r2_web.ws_probe import frame, probe, read_frame


def reader(data):
    buf = bytearray(data)

    def recv(n):
        out = bytes(buf[:n])
        del buf[:n]
        return out
    return recv


def test_client_frame_is_masked_and_reads_back():
    for text in ["hi", "x" * 300, "y" * 70000]:
        op, data = read_frame(reader(frame(text)))
        assert op == 1 and data.decode() == text


def test_server_frame_unmasked():
    payload = b'{"topic": "/a"}'
    assert read_frame(reader(bytes([0x81, len(payload)]) + payload)) == (1, payload)
    big = b"z" * 200
    assert read_frame(reader(bytes([0x81, 126]) + struct.pack("!H", 200) + big)) == (1, big)


def fake_rosbridge(answer):
    """A one-shot server: handshake, read the subscribe, then send `answer` frames (or nothing)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def run():
        c, _ = srv.accept()
        c.recv(4096)
        c.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
        c.recv(4096)
        for a in answer:
            body = json.dumps(a).encode()
            c.sendall(bytes([0x81, len(body)]) + body)
        threading.Event().wait(1.5)
        c.close()
        srv.close()
    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]


def test_probe_true_when_the_topic_comes():
    port = fake_rosbridge([{"op": "status"}, {"op": "publish", "topic": "/web/heartbeat", "msg": {"data": "1"}}])
    assert probe("/web/heartbeat", "std_msgs/msg/String", port=port, wait=2.0)


def test_probe_false_when_silent():
    port = fake_rosbridge([])
    assert not probe("/web/heartbeat", "std_msgs/msg/String", port=port, wait=1.0)


def test_probe_times_out_on_a_server_that_never_answers_the_handshake():
    import pytest
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)          # accepted by the kernel, never answered: like a frozen rosbridge
    with pytest.raises(OSError) as e:
        probe("/web/heartbeat", "std_msgs/msg/String", port=srv.getsockname()[1], wait=1.0)
    assert not isinstance(e.value, ConnectionRefusedError)
    srv.close()
