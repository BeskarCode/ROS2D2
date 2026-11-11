# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The System tab's data about the Pi: the software version (~/r2_ws/VERSION, written by
setup/deploy.sh) and, on demand, its telemetry."""

import glob
import os
import subprocess

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


# ---------- telemetry (only read when the console asks for it) ----------

def parse_meminfo(text):
    """{"total", "available"} in bytes, from /proc/meminfo."""
    kv = {}
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            kv[name.strip()] = int(parts[0]) * 1024
    return {"total": kv.get("MemTotal"), "available": kv.get("MemAvailable")}


def parse_stat(text):
    """[(busy, total)] for the lines cpu, cpu0, cpu1... of /proc/stat (busy = not idle or iowait)."""
    out = []
    for line in text.splitlines():
        if not line.startswith("cpu"):
            continue
        n = [int(x) for x in line.split()[1:]]
        total = sum(n[:8])                # user nice system idle iowait irq softirq steal
        out.append((total - n[3] - (n[4] if len(n) > 4 else 0), total))
    return out


def cpu_percent(prev, cur):
    """% busy of each entry between two parse_stat() samples (0 if no time went by)."""
    out = []
    for (b0, t0), (b1, t1) in zip(prev, cur):
        out.append(round(100.0 * (b1 - b0) / (t1 - t0), 1) if t1 > t0 else 0.0)
    return out


def parse_throttled(value):
    """The Pi firmware's flags from `vcgencmd get_throttled` (throttled=0x50005), or None."""
    try:
        bits = int(value.strip().split("=", 1)[1], 16)
    except (IndexError, ValueError):
        return None
    return {"undervoltage_now": bool(bits & 1), "throttled_now": bool(bits & 4),
            "undervoltage_since_boot": bool(bits & 0x10000), "throttled_since_boot": bool(bits & 0x40000)}


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def throttled_from_hwmon(alarm):
    """Only "under-voltage now", from the kernel's rpi_volt in0_lcrit_alarm text; None if absent."""
    if alarm is None or alarm.strip() not in ("0", "1"):
        return None
    return {"undervoltage_now": alarm.strip() == "1", "throttled_now": None,
            "undervoltage_since_boot": None, "throttled_since_boot": None}


def _rpi_volt_alarm():
    for name in glob.glob("/sys/class/hwmon/hwmon*/name"):
        if (_read(name) or "").strip() == "rpi_volt":
            return _read(os.path.join(os.path.dirname(name), "in0_lcrit_alarm"))
    return None


def _throttled():
    """The Pi's power/heat flags: vcgencmd (Raspberry Pi OS), else the kernel's under-voltage
    alarm (Ubuntu, where /dev/vcio is root-only), else None."""
    try:
        r = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=1)
        if r.returncode == 0 and parse_throttled(r.stdout):
            return parse_throttled(r.stdout)
    except (OSError, subprocess.SubprocessError):
        pass
    return throttled_from_hwmon(_rpi_volt_alarm())


def snapshot(prev_stat):
    """(the Pi's telemetry, this /proc/stat sample for the next call). cpu is None on the
    first call: a percentage needs two samples."""
    st = os.statvfs("/")
    stat_text = _read("/proc/stat")
    stat = parse_stat(stat_text) if stat_text else None
    temp = _read("/sys/class/thermal/thermal_zone0/temp")
    data = {
        "disk": {"total": st.f_blocks * st.f_frsize, "free": st.f_bavail * st.f_frsize},
        "mem": parse_meminfo(_read("/proc/meminfo") or ""),
        "cpu": cpu_percent(prev_stat, stat) if prev_stat and stat else None,
        "temp_c": round(int(temp) / 1000.0, 1) if temp and temp.strip().isdigit() else None,
        "throttled": _throttled(),
    }
    return data, stat


def system_payload(telemetry, prev_stat, version_path=VERSION_FILE):
    """GET /api/system: the version, plus the telemetry when asked. (body, stat for next time)"""
    body = {"version": read_version(version_path)}
    if not telemetry:
        return body, prev_stat
    data, stat = snapshot(prev_stat)
    body.update(data)
    return body, stat
