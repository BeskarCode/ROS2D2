# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The console's web server against a real socket: what the browser may keep (WEB-3)."""
import functools
import http.client
import os
import threading
from http.server import ThreadingHTTPServer

import pytest

from r2_web.web_server_node import Handler


@pytest.fixture
def server(tmp_path):
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "three.js").write_text("three", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("one", encoding="utf-8")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, tmp_path
    srv.shutdown()
    srv.server_close()


def get(srv, path, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.request("GET", path, headers=headers or {})
    r = c.getresponse()
    body = r.read()
    c.close()
    return r, body


def test_pages_revalidated_with_an_etag(server):
    srv, root = server
    r, body = get(srv, "/app.js")
    assert r.status == 200 and body == b"one"
    assert r.getheader("Cache-Control") == "no-cache"
    tag = r.getheader("ETag")
    assert tag
    r, body = get(srv, "/app.js", {"If-None-Match": tag})
    assert r.status == 304 and body == b""
    (root / "app.js").write_text("two!", encoding="utf-8")
    os.utime(root / "app.js", ns=(1, 1))         # changed, with an older time: sent again
    r, body = get(srv, "/app.js", {"If-None-Match": tag, "If-Modified-Since": "Sun, 01 Jan 2040 00:00:00 GMT"})
    assert r.status == 200 and body == b"two!"


def test_index_vendor_and_api(server):
    srv, _ = server
    r, _ = get(srv, "/")
    assert r.status == 200 and r.getheader("ETag")
    r, _ = get(srv, "/vendor/three.js")
    assert r.getheader("Cache-Control") == "public, max-age=604800"
    r, body = get(srv, "/api/ping")
    assert r.status == 200 and r.getheader("Cache-Control") == "no-store" and r.getheader("ETag") is None
    assert b'"ok": true' in body


def post(srv, path, body=b"{}", headers=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.request("POST", path, body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r, data


def test_a_post_from_another_site_is_refused(server):
    # WEB-9: a page of another site, open on a phone on the same WiFi, must not restart R2
    srv, _ = server
    r, _ = post(srv, "/api/nowhere", headers={"Origin": "http://otra"})
    assert r.status == 403
    port = srv.server_address[1]
    r, _ = post(srv, "/api/nowhere", headers={"Origin": f"http://127.0.0.1:{port}"})
    assert r.status == 404                      # its own page: on to the route (none here)


def test_a_bad_content_length_is_refused(server):
    srv, _ = server
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.putrequest("POST", "/api/cameras")
    c.putheader("Content-Length", "-1")
    c.endheaders()
    r = c.getresponse()
    assert r.status == 400
    c.close()


def test_one_connection_serves_several_requests(server):
    # HTTP/1.1: the files of a page, API answers, errors and a POST, one after the other on one socket
    srv, _ = server
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    for method, path, status in [("GET", "/app.js", 200), ("GET", "/api/ping", 200), ("GET", "/nothing.js", 404),
                                 ("POST", "/api/nowhere", 404), ("GET", "/vendor/three.js", 200)]:
        c.request(method, path, body=b"{}" if method == "POST" else None)
        r = c.getresponse()
        r.read()
        assert r.status == status, path
        assert r.version == 11
    c.close()


def test_a_chunked_post_is_refused_and_the_connection_closed(server):
    # REV-3: the chunked body is not read as the next request on the same connection
    srv, _ = server
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.putrequest("POST", "/api/cameras")
    c.putheader("Transfer-Encoding", "chunked")
    c.endheaders()
    c.send(b"5\r\nGET /\r\n0\r\n\r\n")
    r = c.getresponse()
    r.read()
    assert r.status == 400
    assert r.getheader("Connection", "").lower() == "close"
    c.close()
