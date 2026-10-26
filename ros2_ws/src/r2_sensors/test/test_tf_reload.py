import os

from r2_sensors.config import Reloader

ONE = "a:\n  type: vl53l0x\n  x: {x}\n  y: 0\n  z: 0.25\n  pico: {{xshut: 2}}\n"


def write(path, text, bump):
    path.write_text(text, encoding="utf-8")
    t = os.path.getmtime(path) + bump
    os.utime(path, (t, t))


def test_reload_only_when_the_file_changes(tmp_path):
    p = tmp_path / "sensors.yaml"
    write(p, ONE.format(x=0.2), 0)
    r = Reloader(lambda: str(p))
    assert r.poll()["a"]["x"] == 0.2
    assert r.poll() is None
    write(p, ONE.format(x=0.3), 5)
    assert r.poll()["a"]["x"] == 0.3


def test_bad_file_keeps_last_good(tmp_path):
    p = tmp_path / "sensors.yaml"
    write(p, ONE.format(x=0.2), 0)
    r = Reloader(lambda: str(p))
    r.poll()
    write(p, "a: [1", 5)
    assert r.poll() is None
    assert "YAML" in r.error
    assert r.sensors["a"]["x"] == 0.2


def test_switches_to_another_file(tmp_path):
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    write(a, ONE.format(x=0.2), 0)
    write(b, ONE.format(x=0.9), 0)
    current = [str(a)]
    r = Reloader(lambda: current[0])
    r.poll()
    current[0] = str(b)
    assert r.poll()["a"]["x"] == 0.9


def test_missing_file_is_an_error_not_a_crash(tmp_path):
    r = Reloader(lambda: str(tmp_path / "none.yaml"))
    assert r.poll() is None and r.error
