# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Setup -> Sensors -> lidar -> USB: unplug the lidar's USB in software and plug it back, through
the root script /usr/local/sbin/r2-lidar-usb (setup/install_lidar_usb.sh). Apart from ROS so it
can be tested: `run` runs a command and returns (exit code, output), `stop_motor` asks the driver
to stop the motor and returns once it has (or could not)."""
import subprocess

HELPER = "/usr/local/sbin/r2-lidar-usb"
STATES = ("connected", "disconnected", "absent")
NOT_INSTALLED = "not installed: run setup/install_lidar_usb.sh on the Pi once"


def run_helper(arg, timeout=15):
    try:
        p = subprocess.run(["sudo", "-n", HELPER, arg], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout.strip() or p.stderr.strip())


def usb_state(run=run_helper):
    """GET /api/lidar/usb: {"state": connected|disconnected|absent} or {"error": why}."""
    code, out = run("state")
    if code == 0 and out in STATES:
        return 200, {"state": out}
    return 200, {"state": None, "error": NOT_INSTALLED if "sudo" in out or "password" in out else out}


def set_usb(connected, run=run_helper, stop_motor=lambda: None):
    """POST /api/lidar/usb {"connected": bool}. Before unplugging, the motor is stopped: the port
    keeps its 5 V, and a C1 left spinning would keep spinning."""
    if not isinstance(connected, bool):
        return 400, {"error": "connected must be true or false"}
    if not connected:
        stop_motor()
    code, out = run("on" if connected else "off")
    if code == 0:
        return 200, {"state": out.splitlines()[-1] if out else ("connected" if connected else "disconnected")}
    return 409, {"error": NOT_INSTALLED if "sudo" in out or "password" in out else out}
