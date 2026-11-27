# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""What a POST to the console must bring before anything is done with it.

The server listens on every address with no password: a web page open on any phone or PC on
the same WiFi could otherwise send simple POSTs (restart, flash, move the WiFi, overwrite the
YAML files). Browsers say where a request comes from (Origin): it must be this same server.
A request without Origin (curl, scripts on the Pi) is let through."""

from urllib.parse import urlsplit

MAX_BODY = 1024 * 1024        # 1 MiB: the biggest YAML file is a few kB


class BadBody(ValueError):
    pass


def origin_ok(headers):
    origin = headers.get("Origin")
    if origin is None:
        return True
    host = headers.get("Host", "")
    try:
        return bool(host) and urlsplit(origin).netloc.lower() == host.lower()
    except ValueError:
        return False


def body_length(headers, limit=MAX_BODY):
    """Content-Length as a number of bytes to read: 0 when absent; BadBody when it is not a
    number, negative or over the limit (read(-1) would wait until the connection closes)."""
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
