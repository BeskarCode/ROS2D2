# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The Pico firmware from the Pi (System tab): check GitHub for a newer one, and on request
pull, build and flash it. Needs setup/install_pico_toolchain.sh once.

The outside world (commands, the Pico bridge's /pico/release service, the Pico's state, whether
an automatic mode drives the feet) comes in as functions, so this is tested without any of it."""

import os
import re
import subprocess
import threading
import time

CLONE = os.path.expanduser("~/ros2d2-firmware")
ARDUINO_CLI = os.path.expanduser("~/.local/bin/arduino-cli")
FLASH = "/usr/local/sbin/r2-pico-flash"
FIRMWARE = "firmware/r2_pico_sensors"
LOG_LINES = 200
ABBREV = 10                     # build.sh says the commit with this many digits; git's own %h length grows
COMMIT_RE = re.compile(r"^[0-9a-f]{4,40}(-dirty)?$")
STEPS = {"pulling": "Getting the new firmware from GitHub", "compiling": "Building it (a few minutes on a Pi 4)",
         "releasing": "Restarting the Pico into its USB loader", "flashing": "Copying the firmware onto the Pico",
         "waiting": "Waiting for the Pico to come back", "done": "Flashed", "failed": "Failed"}


def autonomous_active(nav, nav_age, follow, follow_age):
    """An automatic mode drives the feet: the navigator (/nav/state) busy in the last 2 s, or
    the colour follower (/follow/state, only published while it is on) in the last 1 s."""
    if nav is not None and nav_age <= 2.0 and nav.get("state") not in ("idle", "gave up", "manual", "arrived"):
        return True
    return follow is not None and follow_age <= 1.0


def same_commit(a, b):
    """Two abbreviations of one commit (older builds used git's %h, 7 digits or more)."""
    return bool(a) and bool(b) and min(len(a), len(b)) >= 7 and (a.startswith(b) or b.startswith(a))


def compare(pico_commit, main_commit, is_ancestor):
    """up_to_date | update (main is newer) | unpublished (the Pico's is not on main) | unknown"""
    if not pico_commit or not COMMIT_RE.match(pico_commit) or not main_commit or not COMMIT_RE.match(main_commit):
        return "unknown"            # also keeps anything but a hex commit away from git's command line
    if pico_commit.endswith("-dirty"):
        return "unpublished"
    if same_commit(pico_commit, main_commit):
        return "up_to_date"
    return "update" if is_ancestor(pico_commit, main_commit) else "unpublished"


def run_command(cmd, timeout, env=None):
    """(exit code, output) of a command; never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, **(env or {})})
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"{cmd[0]}: took more than {timeout} s"
    except OSError as e:
        return 127, f"{cmd[0]}: {e.strerror}"


def toolchain_installed():
    return os.path.isfile(ARDUINO_CLI) and os.path.isdir(os.path.join(CLONE, ".git")) and os.path.isfile(FLASH)


class FirmwareJob:
    """One check or flash at a time, in its own thread; status() is what the page shows."""

    def __init__(self, run=run_command, release=None, pico_state=lambda: None, autonomous=lambda: False,
                 installed=toolchain_installed, is_ancestor=None, clone=CLONE, sleep=time.sleep, wait_s=30.0):
        self.run, self.release, self.pico_state, self.autonomous = run, release, pico_state, autonomous
        self.installed, self.clone, self.sleep, self.wait_s = installed, clone, sleep, wait_s
        self.is_ancestor = is_ancestor or (lambda a, b: self.run(
            ["git", "-C", self.clone, "merge-base", "--is-ancestor", a, b], 10)[0] == 0)
        self.lock = threading.Lock()
        self.check_lock = threading.Lock()
        self.thread = None
        self.state = "idle"
        self.error = None
        self.log = []
        self.failed_after_release = False
        self.built = None               # the commit the last build said
        self.main = None
        self.internet = None
        self.cmp = "unknown"

    # ---------- what the page sees ----------
    def status(self):
        pico = self.pico_state() or {}
        return {"installed": self.installed(), "state": self.state, "step_text": STEPS.get(self.state, ""),
                "error": self.error, "log": self.log[-LOG_LINES:], "can_retry": self.state == "failed" and self.failed_after_release,
                "pico_commit": pico.get("commit"), "main": self.main, "internet": self.internet, "compare": self.cmp}

    def _note(self, text):
        self.log.extend(text.splitlines())
        del self.log[:-LOG_LINES]

    def _step(self, state, cmd, timeout, env=None):
        self.state = state
        self._note(f"$ {' '.join(cmd)}")
        code, out = self.run(cmd, timeout, env)
        if out:
            self._note(out)
        if code != 0:
            raise RuntimeError(f"{STEPS[state]}: failed ({out.splitlines()[-1] if out else f'exit {code}'})")
        return out

    # ---------- check ----------
    def check(self):
        """git fetch, then compare main's firmware commit with the Pico's. No internet is no failure.
        While a flash runs it leaves git alone (a fetch beside its pull can trip on git's locks)."""
        if self.state not in ("idle", "done", "failed"):
            return
        if not self.check_lock.acquire(blocking=False):
            return                      # another tab is checking: its answer is the same
        try:
            self._check()
        finally:
            self.check_lock.release()

    def _check(self):
        code, out = self.run(["git", "-C", self.clone, "fetch", "--quiet", "origin", "main"], 15)
        self.internet = code == 0
        if not self.internet:
            self._note(out or "git fetch failed")
            return
        code, out = self.run(["git", "-C", self.clone, "log", "-1", f"--abbrev={ABBREV}", "--format=%h|%s|%cI", "origin/main", "--", FIRMWARE], 5)
        parts = out.split("|", 2) if code == 0 else []
        if len(parts) != 3:
            self.main, self.cmp = None, "unknown"
            return
        self.main = {"commit": parts[0], "subject": parts[1], "date": parts[2]}
        self.cmp = compare((self.pico_state() or {}).get("commit"), parts[0], self.is_ancestor)

    # ---------- flash ----------
    def _start(self, target):
        with self.lock:
            if self.state not in ("idle", "done", "failed"):
                return "busy"
            if not self.installed():
                return "not installed"
            if self.autonomous():
                return "blocked"
            self.state, self.error = "starting", None
            self.thread = threading.Thread(target=target, daemon=True)
            self.thread.start()
            return "ok"

    def flash(self):
        return self._start(self._flash)

    def retry(self):
        if not (self.state == "failed" and self.failed_after_release and self.built):
            return "nothing to retry"
        return self._start(self._copy)

    def wait(self, timeout=None):
        if self.thread:
            self.thread.join(timeout)

    def _fail(self, e):
        self.state, self.error = "failed", str(e)
        self._note(f"failed: {e}")

    def _flash(self):
        self.log, self.failed_after_release = [], False
        try:
            self._step("pulling", ["git", "-C", self.clone, "pull", "--ff-only"], 120)
            out = self._step("compiling", [os.path.join(self.clone, FIRMWARE, "build.sh"), "--jobs", "2", "--nice"], 1200,
                             env={"ARDUINO_CLI": ARDUINO_CLI})
            m = re.search(r"^build: r2_pico_sensors commit (\S+)", out, re.M)
            if not m:
                raise RuntimeError("the build did not say which commit it built")
            self.built = m.group(1)
        except Exception as e:          # anything: the job must end, never stay 'busy'
            self._fail(e)
            return
        self._copy()

    def _copy(self):
        self.failed_after_release = True
        released = False
        try:
            # checked again here: a mode may have started during the minutes of the build, and
            # from here on the Pico's sensors are gone until it is back
            if self.autonomous():
                raise RuntimeError("an automatic mode is driving: stop it and press Retry")
            self.state = "releasing"
            self._note("/pico/release true")
            released = True             # even a failed call may have left the bridge released
            if not self.release(True):
                raise RuntimeError("the Pico bridge did not let go of the Pico")
            self._step("flashing", ["sudo", "-n", FLASH], 30)
            self.state = "waiting"
            self._note("/pico/release false")
            released = False
            self.release(False)
            end = time.monotonic() + self.wait_s
            while time.monotonic() < end:
                pico = self.pico_state() or {}
                if pico.get("connected") and same_commit(pico.get("commit"), self.built):
                    self.state, self.failed_after_release, self.cmp = "done", False, "up_to_date"
                    self._note(f"the Pico runs {self.built}")
                    return
                self.sleep(0.5)
            now = (self.pico_state() or {}).get("commit")
            raise RuntimeError(f"the Pico did not come back with {self.built} (it says {now})")
        except Exception as e:
            if released:
                try:
                    self.release(False)
                except Exception as e2:
                    self._note(f"/pico/release false failed: {e2}")
            self._fail(e)
