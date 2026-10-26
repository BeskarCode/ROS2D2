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
