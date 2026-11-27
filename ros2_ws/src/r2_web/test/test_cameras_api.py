# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import os

from r2_camera.config import load_cameras
from r2_web.cameras_api import ModesCache, save_cameras

GOOD = "cam1:\n  source: /dev/video0\n  yaw_deg: 10\n"


def test_saved_whole_and_readable(tmp_path):
    user = str(tmp_path / "cfg" / "cameras.yaml")
    code, body = save_cameras({"yaml": GOOD}, user)
    assert code == 200 and body["file"] == user
    assert load_cameras(user)["cam1"]["yaw_deg"] == 10
    assert not os.path.exists(user + ".tmp")


def test_a_bad_file_leaves_the_old_one_alone(tmp_path):
    user = str(tmp_path / "cameras.yaml")
    assert save_cameras({"yaml": GOOD}, user)[0] == 200
    for bad in ({"yaml": "- a\n- b\n"}, {"yaml": "cam1: [1, 2\n"}, {"yaml": "cam1: 3\n"}, {"yaml": 5}, {}):
        code, body = save_cameras(bad, user)
        assert code == 400, bad
        assert body["error"].startswith("not saved")
    assert load_cameras(user)["cam1"]["yaw_deg"] == 10
    assert not os.path.exists(user + ".tmp")


def test_a_body_that_is_not_an_object_is_refused(tmp_path):
    for bad in ([1, 2], "text", None, 7):
        assert save_cameras(bad, str(tmp_path / "c.yaml"))[0] == 400


class _Stat:
    def __init__(self, ino, ctime):
        self.st_ino, self.st_ctime = ino, ctime


def test_modes_asked_once_per_plugged_camera():
    # WEB-2: v4l2-ctl once per camera, not on every GET /api/cameras; plugged again: asked again
    calls = []
    stats = {"/dev/video0": _Stat(1, 10.0)}

    def list_modes(dev, fourcc):
        calls.append(dev)
        return ["640x480@30"]
    c = ModesCache(list_modes, stat=lambda d: stats[d])
    assert c.get("/dev/video0") == ["640x480@30"]
    assert c.get("/dev/video0") == ["640x480@30"]
    assert calls == ["/dev/video0"]
    stats["/dev/video0"] = _Stat(2, 20.0)            # unplugged and plugged back
    c.get("/dev/video0")
    assert len(calls) == 2


def test_modes_of_a_device_that_is_gone_are_not_cached():
    calls = []

    def stat(d):
        raise FileNotFoundError(d)
    c = ModesCache(lambda d, f: calls.append(d) or [], stat=stat)
    c.get("/dev/video9")
    c.get("/dev/video9")
    assert len(calls) == 2


def test_a_failed_v4l2_ctl_is_not_kept():
    # REV-1: a camera starting or busy makes v4l2-ctl fail ([]); that must not stick until it is replugged
    answers = [[], ["640x480@30"]]
    calls = []

    def list_modes(dev, fourcc):
        calls.append(dev)
        return answers[len(calls) - 1]
    c = ModesCache(list_modes, stat=lambda d: _Stat(1, 10.0))
    assert c.get("/dev/video0") == []
    assert c.get("/dev/video0") == ["640x480@30"]
    assert c.get("/dev/video0") == ["640x480@30"]
    assert len(calls) == 2


def test_two_saves_at_once_leave_one_whole_file(tmp_path):
    # REV-2: each HTTP request has its own thread; two saves must not mix in the same temporary file
    import threading
    user = str(tmp_path / "cameras.yaml")
    texts = ["".join(f"cam{i}:\n  yaw_deg: {k}\n" for i in range(300)) for k in (1, 2)]
    out = []
    go = threading.Barrier(2)

    def save(t):
        go.wait()
        for _ in range(20):
            out.append(save_cameras({"yaml": t}, user)[0])
    th = [threading.Thread(target=save, args=(t,)) for t in texts]
    [t.start() for t in th]
    [t.join() for t in th]
    assert set(out) == {200}
    assert open(user, encoding="utf-8").read() in texts
    assert not os.path.exists(user + ".tmp")
