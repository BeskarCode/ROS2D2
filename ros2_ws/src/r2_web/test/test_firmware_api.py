# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.firmware_api import FirmwareJob, autonomous_active, compare


def test_autonomous_active():
    assert not autonomous_active(None, 99, None, 99)
    assert not autonomous_active({"state": "idle"}, 0.5, None, 99)
    assert not autonomous_active({"state": "gave up"}, 0.5, None, 99)
    assert not autonomous_active({"state": "manual"}, 0.5, None, 99)        # the controller drives
    assert not autonomous_active({"state": "arrived"}, 0.5, None, 99)
    assert autonomous_active({"state": "going"}, 0.5, None, 99)
    assert not autonomous_active({"state": "going"}, 2.5, None, 99)          # the navigator went quiet
    assert autonomous_active(None, 99, {"state": "waiting"}, 0.3)              # follow publishes only while on
    assert not autonomous_active(None, 99, {"state": "following"}, 1.5)


def test_compare():
    anc = lambda a, b: (a, b) == ("1500ee7", "a8fc309")      # 1500ee7 came before a8fc309
    assert compare("a8fc309", "a8fc309", anc) == "up_to_date"
    assert compare("1500ee7", "a8fc309", anc) == "update"
    assert compare("1234567", "a8fc309", anc) == "unpublished"          # built from another branch
    assert compare("a8fc309-dirty", "a8fc309", anc) == "unpublished"    # built with changes not committed
    assert compare(None, "a8fc309", anc) == "unknown"                   # firmware before 0.2.0
    assert compare("unknown", "a8fc309", anc) == "unknown"


class Fake:
    """The outside world of a FirmwareJob: commands, the bridge and the Pico's state."""

    def __init__(self, fail=None, pico_after=None):
        self.calls, self.releases = [], []
        self.fail = fail                        # a word of the command that fails
        self.pico = {"commit": "1500ee7", "connected": True}
        self.pico_after = pico_after or "a8fc309"
        self.active = False

    def run(self, cmd, timeout, env=None):
        self.calls.append(" ".join(cmd))
        line = " ".join(cmd)
        if self.fail and self.fail in line:
            return 1, f"{self.fail} went wrong"
        if "build.sh" in line:
            return 0, "build: r2_pico_sensors commit a8fc309\nSketch uses 77432 bytes"
        if "rev-parse" in line or "log -1" in line:
            return 0, "a8fc309|Pico firmware 0.2.0|2026-11-12T00:30:00+01:00"
        return 0, ""

    def release(self, on):
        self.releases.append(on)
        if not on:
            self.pico = {"commit": self.pico_after, "connected": True}
        return True


def job(fake, **kw):
    return FirmwareJob(run=fake.run, release=fake.release, pico_state=lambda: fake.pico,
                       autonomous=lambda: fake.active, installed=lambda: True, sleep=lambda s: None,
                       wait_s=0.05, **kw)


def test_flash_all_the_way():
    f = Fake()
    j = job(f)
    assert j.flash() == "ok"
    j.wait()
    s = j.status()
    assert s["state"] == "done" and s["error"] is None, s
    assert f.releases == [True, False]
    order = [next(i for i, c in enumerate(f.calls) if w in c) for w in ("pull", "build.sh", "r2-pico-flash")]
    assert order == sorted(order)
    assert any("--jobs 2" in c and "--nice" in c for c in f.calls)


def test_build_fails_the_pico_is_left_alone():
    f = Fake(fail="build.sh")
    j = job(f)
    j.flash()
    j.wait()
    s = j.status()
    assert s["state"] == "failed" and "build.sh went wrong" in "\n".join(s["log"])
    assert f.releases == []                         # never asked for the port
    assert not s["can_retry"]


def test_copy_fails_the_port_is_given_back_and_retry_skips_the_build():
    f = Fake(fail="r2-pico-flash")
    j = job(f)
    j.flash()
    j.wait()
    s = j.status()
    assert s["state"] == "failed" and s["can_retry"]
    assert f.releases == [True, False]               # given back even so
    f.fail = None
    builds = sum("build.sh" in c for c in f.calls)
    assert j.retry() == "ok"
    j.wait()
    assert j.status()["state"] == "done"
    assert sum("build.sh" in c for c in f.calls) == builds


def test_the_pico_does_not_come_back_with_the_new_firmware():
    f = Fake(pico_after="1500ee7")
    j = job(f)
    j.flash()
    j.wait()
    s = j.status()
    assert s["state"] == "failed" and "a8fc309" in s["error"]


def test_one_flash_at_a_time_and_never_with_an_automatic_mode():
    f = Fake()
    j = job(f)
    j.state = "compiling"                            # as if one were running
    assert j.flash() == "busy"
    j.state = "idle"
    f.active = True
    assert j.flash() == "blocked" and f.calls == []


def test_check_without_internet_is_not_a_failure():
    f = Fake(fail="fetch")
    j = job(f)
    j.check()
    s = j.status()
    assert s["internet"] is False and s["state"] == "idle" and s["compare"] == "unknown"


def test_check_finds_an_update():
    f = Fake()
    j = job(f, is_ancestor=lambda a, b: (a, b) == ("1500ee7", "a8fc309"))
    j.check()
    s = j.status()
    assert s["internet"] is True and s["compare"] == "update"
    assert s["main"] == {"commit": "a8fc309", "subject": "Pico firmware 0.2.0", "date": "2026-11-12T00:30:00+01:00"}
