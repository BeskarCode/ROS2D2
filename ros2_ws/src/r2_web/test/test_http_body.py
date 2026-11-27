# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import pytest

from r2_web.http_body import MAX_BODY, BadBody, body_length, origin_ok


def test_origin_must_be_this_server():
    assert origin_ok({"Host": "10.42.0.1:8080", "Origin": "http://10.42.0.1:8080"})
    assert origin_ok({"Host": "r2pi.local:8080", "Origin": "http://R2PI.local:8080"})
    assert origin_ok({"Host": "10.42.0.1:8080"})                       # no Origin: curl, scripts
    assert not origin_ok({"Host": "10.42.0.1:8080", "Origin": "http://otra"})
    assert not origin_ok({"Host": "10.42.0.1:8080", "Origin": "http://10.42.0.1:9999"})
    assert not origin_ok({"Host": "10.42.0.1:8080", "Origin": "null"})
    assert not origin_ok({"Origin": "http://10.42.0.1:8080"})


def test_body_length():
    assert body_length({}) == 0
    assert body_length({"Content-Length": "12"}) == 12
    assert body_length({"Content-Length": str(MAX_BODY)}) == MAX_BODY
    for bad in ("-1", "abc", "1.5", str(MAX_BODY + 1)):
        with pytest.raises(BadBody):
            body_length({"Content-Length": bad})


def test_a_chunked_body_is_refused():
    # REV-3: without a Content-Length a chunked body would be read as the next request
    with pytest.raises(BadBody):
        body_length({"Transfer-Encoding": "chunked"})


def test_dns_rebinding_is_refused():
    # REV-8: someone else's domain pointing at the Pi sends Origin and Host alike, but not one of the Pi's names
    from r2_web.http_body import own_names
    import socket
    names = own_names(["192.168.68.112/24", "10.42.0.1/24"])
    me = socket.gethostname().lower()
    assert not origin_ok({"Host": "evil.example:8080", "Origin": "http://evil.example:8080"}, names)
    for host in ("192.168.68.112:8080", "10.42.0.1:8080", f"{me}.local:8080", f"{me}:8080",
                 "localhost:8080", "127.0.0.1:8080", "[::1]:8080"):
        assert origin_ok({"Host": host, "Origin": f"http://{host}"}, names), host
    assert origin_ok({"Host": "evil.example:8080"}, names)       # no Origin: curl, scripts on the Pi
