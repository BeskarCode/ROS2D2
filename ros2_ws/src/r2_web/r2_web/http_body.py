# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""What a POST to the console must bring before anything is done with it.

The server listens on every address with no password: a web page open on any phone or PC on
the same WiFi could otherwise send simple POSTs (restart, flash, move the WiFi, overwrite the
YAML files). Browsers say where a request comes from (Origin): it must be this same server, and
the server must have been asked by one of its own names (its host name, <name>.local, localhost
or one of its addresses), not by a domain of someone else's that points at the Pi (DNS
rebinding: then Origin and Host match but are not the Pi's). A request without Origin (curl,
scripts on the Pi) is let through."""

import socket
from urllib.parse import urlsplit

MAX_BODY = 1024 * 1024        # 1 MiB: the biggest YAML file is a few kB


class BadBody(ValueError):
    pass


def own_names(addresses=()):
    """The names the Pi answers to: localhost, its host name and <name>.local, and its addresses
    ("a.b.c.d/nn" from system_api.addresses() is fine)."""
    name = socket.gethostname().lower()
    out = {"localhost", "127.0.0.1", "::1", name, f"{name}.local"}
    out.update(a.split("/")[0].lower() for a in addresses)
    return out


def _host_name(host):
    """'r2pi.local:8080' -> 'r2pi.local'; '[::1]:8080' -> '::1'."""
    try:
        return (urlsplit(f"//{host}").hostname or "").lower()
    except ValueError:
        return ""


def origin_ok(headers, names=None):
    """names: the Pi's own names (own_names()); None skips that part (tests of the Origin alone)."""
    origin = headers.get("Origin")
    if origin is None:
        return True
    host = headers.get("Host", "")
    try:
        same = bool(host) and urlsplit(origin).netloc.lower() == host.lower()
    except ValueError:
        return False
    return same and (names is None or _host_name(host) in names)


def body_length(headers, limit=MAX_BODY):
    """Content-Length as a number of bytes to read: 0 when absent; BadBody when it is not a
    number, negative or over the limit (read(-1) would wait until the connection closes)."""
    if headers.get("Transfer-Encoding"):
        # a chunked body would stay on the connection and be read as the next request
        raise BadBody("send the body with a Content-Length, not a Transfer-Encoding")
    raw = headers.get("Content-Length")
    if raw in (None, ""):
        return 0
    try:
        n = int(raw)
    except ValueError:
        raise BadBody(f"bad Content-Length {raw!r}") from None
    if n < 0:
        raise BadBody(f"bad Content-Length {raw!r}")
    if n > limit:
        raise BadBody(f"body too big ({n} bytes, at most {limit})")
    return n
