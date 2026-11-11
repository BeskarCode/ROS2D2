# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The System tab's data about the Pi: the software version (~/r2_ws/VERSION, written by
setup/deploy.sh) and, on demand, its telemetry."""

import os

VERSION_FILE = os.path.expanduser("~/r2_ws/VERSION")


def read_version(path=VERSION_FILE):
    """{"commit", "date", "dirty"} from the VERSION file, or {"commit": None} if there is none."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {"commit": None}
    kv = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    commit = kv.get("commit", "").strip()
    if not commit:
        return {"commit": None}
    return {"commit": commit, "date": kv.get("date", "").strip() or None, "dirty": kv.get("dirty", "").strip() == "1"}
