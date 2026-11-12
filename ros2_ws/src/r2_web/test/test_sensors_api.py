# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.sensors_api import save_sensors, sensors_payload

GOOD = "tof_front:\n  type: vl53l0x\n  x: 0.2\n  y: 0\n  z: 0.25\n  pico: {xshut: 2}\n"
BAD = "tof_front:\n  type: vl53l0x\n  x: 0.2\n  y: 0\n  z: 0.25\n"


def files(tmp_path):
    default = tmp_path / "pkg.yaml"
    default.write_text(GOOD, encoding="utf-8")
    return str(default), str(tmp_path / "user" / "sensors.yaml")


def test_package_file_when_nothing_saved(tmp_path):
    default, user = files(tmp_path)
    p = sensors_payload(default, user, str(tmp_path / "no-lidar"))
    assert p["saved"] is False and p["file"] == default and p["yaml"] == GOOD
    assert list(p["sensors"]) == ["tof_front"] and p["error"] is None
    assert p["lidar_device"] is False


def test_saved_file_wins(tmp_path):
    default, user = files(tmp_path)
    assert save_sensors(GOOD.replace("0.2", "0.3"), user)[0] == 200
    p = sensors_payload(default, user, str(tmp_path / "no-lidar"))
    assert p["saved"] is True and p["sensors"]["tof_front"]["x"] == 0.3


def test_broken_saved_file_is_reported_not_raised(tmp_path):
    default, user = files(tmp_path)
    save_sensors(GOOD, user)
    with open(user, "w", encoding="utf-8") as f:
        f.write(BAD)
    p = sensors_payload(default, user, str(tmp_path / "no-lidar"))
    assert p["sensors"] == {} and "tof_front" in p["error"] and p["yaml"] == BAD


def test_lidar_device_present(tmp_path):
    default, user = files(tmp_path)
    dev = tmp_path / "r2-lidar"
    dev.write_text("")
    assert sensors_payload(default, user, str(dev))["lidar_device"] is True


def test_save_adds_final_newline(tmp_path):
    _, user = files(tmp_path)
    code, body = save_sensors(GOOD.rstrip("\n"), user)
    assert code == 200 and body == {"ok": True, "file": user}
    with open(user, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_bad_save_keeps_the_old_file(tmp_path):
    _, user = files(tmp_path)
    save_sensors(GOOD, user)
    code, body = save_sensors(BAD, user)
    assert code == 400 and body["error"].startswith("not saved: tof_front: pico")
    with open(user, encoding="utf-8") as f:
        assert f.read() == GOOD


# ---------- in use / ignored switch ----------
from r2_web.sensors_api import set_enabled  # noqa: E402

TWO = ("# my comment\n"
       "tof_a:\n  type: vl53l0x\n  x: 0.2\n  y: 0\n  z: 0.25\n  pico: {xshut: 2}\n"
       "tof_b:\n  type: vl53l0x\n  x: 0.2\n  y: 0.1\n  z: 0.25\n  pico: {xshut: 3}\n")


def test_set_enabled_changes_only_that_line(tmp_path):
    user = tmp_path / "user" / "sensors.yaml"
    user.parent.mkdir()
    user.write_text(TWO, encoding="utf-8")
    code, body = set_enabled(str(tmp_path / "pkg.yaml"), str(user), "tof_b", False)
    assert code == 200, body
    after = user.read_text(encoding="utf-8")
    assert after == TWO.replace("tof_b:\n  type: vl53l0x\n", "tof_b:\n  type: vl53l0x\n  enabled: false\n")
    assert set_enabled(str(tmp_path / "pkg.yaml"), str(user), "tof_b", True)[0] == 200
    assert user.read_text(encoding="utf-8") == after.replace("  enabled: false\n", "  enabled: true\n")


def test_set_enabled_starts_from_the_package_file(tmp_path):
    pkg = tmp_path / "pkg.yaml"
    pkg.write_text(TWO, encoding="utf-8")
    user = tmp_path / "user" / "sensors.yaml"
    assert set_enabled(str(pkg), str(user), "tof_a", False)[0] == 200
    assert "tof_a:\n  type: vl53l0x\n  enabled: false\n" in user.read_text(encoding="utf-8")
    assert pkg.read_text(encoding="utf-8") == TWO


def test_set_enabled_unknown_sensor(tmp_path):
    pkg = tmp_path / "pkg.yaml"
    pkg.write_text(TWO, encoding="utf-8")
    code, body = set_enabled(str(pkg), str(tmp_path / "u.yaml"), "tof_x", False)
    assert code == 400 and "unknown" in body["error"]


def test_set_enabled_broken_file(tmp_path):
    user = tmp_path / "u.yaml"
    user.write_text("tof_a: [broken", encoding="utf-8")
    code, body = set_enabled(str(tmp_path / "pkg.yaml"), str(user), "tof_a", False)
    assert code == 400 and user.read_text(encoding="utf-8") == "tof_a: [broken"
