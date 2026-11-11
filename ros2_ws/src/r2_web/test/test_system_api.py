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
