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
