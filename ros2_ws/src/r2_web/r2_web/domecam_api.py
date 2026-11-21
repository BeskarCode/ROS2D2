# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Setup -> System -> telemetry of the network cameras (the ESP32 dome cameras): GET /api/domecams
asks each camera in cameras.yaml with an http source for its /status, all at once, and passes it
on. The browser cannot reach them itself: they live on the droid's own WiFi. Only asked while the
System tab shows the telemetry. Apart from ROS so it can be tested."""
import json
import threading
import time
import urllib.parse
import urllib.request


def status_url(source):
    """http://cam:81/stream -> http://cam/status (port 80), or None for a camera that is not on
    the network."""
    if not isinstance(source, str) or not source.startswith(("http://", "https://")):
        return None
    u = urllib.parse.urlsplit(source)
    if not u.hostname:
        return None
    return f"{u.scheme}://{u.hostname}/status"


def fetch_status(url, timeout=1.5):
    t0 = time.monotonic()
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = json.loads(r.read(8192).decode("utf-8", "replace"))
    return body, round((time.monotonic() - t0) * 1000)


def domecams_payload(cameras, fetch=fetch_status):
    """{"cameras": [{"name", "url", "status" | "error", "ms"}]} for every network camera."""
    out, threads = [], []
    for name, params in (cameras or {}).items():
        url = status_url((params or {}).get("source"))
        if not url:
            continue
        item = {"name": name, "url": url}
        out.append(item)

        def ask(item=item):
            try:
                item["status"], item["ms"] = fetch(item["url"])
            except Exception as e:   # off, out of range, busy...
                item["error"] = str(getattr(e, "reason", e)) or type(e).__name__
        t = threading.Thread(target=ask, daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join(2.5)
    for item in out:
        if "status" not in item and "error" not in item:
            item["error"] = "no answer"
    return {"cameras": out}
