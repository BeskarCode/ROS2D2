# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Setup -> System -> R2's WiFi: the channel of R2's own access point, how busy the three usable
channels are, and moving it to the quietest. The picking is r2-wifi-channel's (setup/), run by
hostapd itself each time it starts; this only reads what it found, asks it for a fresh look
(survey, the AP stays up) or restarts hostapd so it picks again. Apart from ROS so it can be tested."""
import json
import subprocess

HELPER = "/usr/local/sbin/r2-wifi-channel"
STATE = "/run/r2-wifi-channel.json"
NOT_INSTALLED = "not installed: run setup/install_wifi_channel.sh on the Pi once"


def run_cmd(cmd, timeout=40):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout.strip() or p.stderr.strip())


def last_pick(path=None):
    """GET /api/wifi: what the last pick (when the AP started) found, or {} before any."""
    try:
        with open(path or STATE, encoding="utf-8") as f:
            return 200, {"pick": json.load(f)}
    except (OSError, ValueError):
        return 200, {"pick": None, "error": NOT_INSTALLED}


def survey(run=run_cmd):
    """POST /api/wifi/survey: how busy each channel is now (the AP stays up)."""
    code, out = run(["sudo", "-n", HELPER, "survey"])
    if code != 0:
        return 409, {"error": NOT_INSTALLED if "sudo" in out or "password" in out else out}
    try:
        return 200, {"survey": json.loads(out.splitlines()[-1])}
    except (ValueError, IndexError):
        return 500, {"error": f"unexpected answer: {out[:200]}"}


def move(run=run_cmd):
    """POST /api/wifi/move: restart the AP, which picks the quietest channel as it starts. The
    camera and anything else on R2's WiFi drop for a few seconds."""
    code, out = run(["sudo", "-n", "systemctl", "restart", "hostapd"], timeout=60)
    if code != 0:
        return 409, {"error": NOT_INSTALLED if "sudo" in out or "password" in out else out}
    return last_pick()
