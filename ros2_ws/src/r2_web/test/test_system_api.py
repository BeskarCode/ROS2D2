# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.system_api import read_version


def test_read_version_ok(tmp_path):
    p = tmp_path / "VERSION"
    p.write_text("commit=265a841\ndate=2026-11-11T23:50:00+01:00\ndirty=1\n", encoding="utf-8")
    assert read_version(str(p)) == {"commit": "265a841", "date": "2026-11-11T23:50:00+01:00", "dirty": True}


def test_read_version_missing(tmp_path):
    assert read_version(str(tmp_path / "nope")) == {"commit": None}


def test_read_version_garbage(tmp_path):
    p = tmp_path / "VERSION"
    p.write_text("hello\ndate=2026-11-11\n", encoding="utf-8")
    assert read_version(str(p)) == {"commit": None}
    p.write_text("rubbish line\ncommit=abc1234\ndirty=0\n", encoding="utf-8")
    assert read_version(str(p)) == {"commit": "abc1234", "date": None, "dirty": False}


from r2_web import system_api
from r2_web.system_api import cpu_percent, parse_meminfo, parse_stat, parse_throttled, system_payload

MEMINFO = "MemTotal:        3884000 kB\nMemFree:          100000 kB\nMemAvailable:    2000000 kB\nBuffers: 1 kB\n"
STAT1 = "cpu  100 0 100 700 100 0 0 0 0 0\ncpu0 50 0 50 350 50 0 0 0 0 0\ncpu1 50 0 50 350 50 0 0 0 0 0\nintr 1 2 3\n"
STAT2 = "cpu  200 0 200 800 100 0 0 0 0 0\ncpu0 150 0 150 450 50 0 0 0 0 0\ncpu1 50 0 50 350 50 0 0 0 0 0\nintr 1 2 3\n"


def test_parse_meminfo():
    assert parse_meminfo(MEMINFO) == {"total": 3884000 * 1024, "available": 2000000 * 1024}


def test_parse_stat_and_cpu_percent():
    a, b = parse_stat(STAT1), parse_stat(STAT2)
    assert a[0] == (200, 1000) and len(a) == 3          # busy = total - idle - iowait
    assert cpu_percent(a, b) == [66.7, 66.7, 0.0]        # cpu: 200 of 300; cpu0: 200 of 300; cpu1 no change


def test_parse_throttled():
    assert parse_throttled("throttled=0x50005") == {"undervoltage_now": True, "throttled_now": True,
                                                    "undervoltage_since_boot": True, "throttled_since_boot": True}
    assert parse_throttled("throttled=0x0") == {"undervoltage_now": False, "throttled_now": False,
                                               "undervoltage_since_boot": False, "throttled_since_boot": False}
    assert parse_throttled("garbage") is None


def test_api_system_without_telemetry_reads_only_version(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise AssertionError("telemetry read without being asked")
    monkeypatch.setattr(system_api, "snapshot", boom)
    assert system_payload(False, None, version_path=str(tmp_path / "none")) == ({"version": {"commit": None}}, None)


def test_api_system_with_telemetry(monkeypatch, tmp_path):
    monkeypatch.setattr(system_api, "snapshot", lambda prev: ({"cpu": None}, "stat"))
    body, prev = system_payload(True, None, version_path=str(tmp_path / "none"))
    assert body == {"version": {"commit": None}, "cpu": None} and prev == "stat"


def test_undervoltage_from_hwmon_when_vcgencmd_cannot_run():
    # Ubuntu: /dev/vcio is root-only, but the kernel's rpi_volt hwmon has the under-voltage alarm
    from r2_web.system_api import throttled_from_hwmon
    assert throttled_from_hwmon("1\n") == {"undervoltage_now": True, "throttled_now": None,
                                           "undervoltage_since_boot": None, "throttled_since_boot": None}
    assert throttled_from_hwmon("0\n")["undervoltage_now"] is False
    assert throttled_from_hwmon(None) is None
