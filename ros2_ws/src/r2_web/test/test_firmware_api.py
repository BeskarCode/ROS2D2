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


def test_compare_abbreviations_of_different_length_are_the_same_commit():
    anc = lambda a, b: False
    assert compare("a8fc309", "a8fc3091b2", anc) == "up_to_date"      # Pico built with 7, main read with 10
    assert compare("a8fc3091b2", "a8fc309", anc) == "up_to_date"
    assert compare("a8fc3091b2-dirty", "a8fc3091b2", anc) == "unpublished"


def test_compare_never_hands_git_an_option():
    seen = []
    anc = lambda a, b: seen.append((a, b)) or True
    assert compare("--output=/tmp/x", "a8fc309", anc) == "unknown"
    assert compare("a8fc309 x", "1500ee7", anc) == "unknown"
    assert seen == []


def test_check_reads_main_with_a_fixed_abbreviation():
    f = Fake()
    job(f).check()
    assert any("log -1" in c and "--abbrev=10" in c for c in f.calls)


def test_check_while_flashing_does_not_touch_git():
    f = Fake()
    j = job(f)
    j.state = "pulling"
    j.check()
    assert f.calls == []


def test_an_automatic_mode_started_during_the_build_stops_the_copy():
    f = Fake()
    real_run = f.run

    def run(cmd, timeout, env=None):
        if "build.sh" in " ".join(cmd):
            f.active = True                      # someone starts patrol while it builds
        return real_run(cmd, timeout, env)
    f.run = run
    j = job(f)
    j.flash()
    j.wait()
    s = j.status()
    assert s["state"] == "failed" and "automatic mode" in s["error"] and s["can_retry"], s
    assert True not in f.releases                    # the Pico kept its sensors
    assert not any("r2-pico-flash" in c for c in f.calls)


def test_a_build_without_its_commit_line_fails_before_the_copy():
    f = Fake()
    real_run = f.run
    f.run = lambda cmd, t, env=None: (0, "Sketch uses 77432 bytes") if "build.sh" in " ".join(cmd) else real_run(cmd, t, env)
    j = job(f)
    j.flash()
    j.wait()
    s = j.status()
    assert s["state"] == "failed" and "commit" in s["error"]
    assert f.releases == []


def test_done_says_up_to_date():
    f = Fake()
    j = job(f)
    j.cmp = "update"
    j.flash()
    j.wait()
    assert j.status()["state"] == "done" and j.status()["compare"] == "up_to_date"


def test_an_unexpected_error_gives_the_port_back_and_frees_the_job():
    f = Fake()
    calls = []

    def release(on):
        calls.append(on)
        if on is True and len(calls) == 1:
            return True
        return True
    f.release = release

    def boom():
        raise ValueError("ros went away")
    j = FirmwareJob(run=f.run, release=release, pico_state=boom, autonomous=lambda: False,
                    installed=lambda: True, sleep=lambda s: None, wait_s=0.05)
    j.flash()
    j.wait()
    s = j.state
    assert s == "failed" and "ros went away" in j.error
    assert calls[-1] is False
