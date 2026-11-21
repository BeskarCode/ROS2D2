# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.domecam_api import domecams_payload, status_url


def test_status_url_from_the_stream_source():
    assert status_url("http://10.42.0.61:81/stream") == "http://10.42.0.61/status"
    assert status_url("http://r2-domecam1.local:81/stream") == "http://r2-domecam1.local/status"
    assert status_url("/dev/video0") is None and status_url(0) is None and status_url(None) is None


def test_only_network_cameras_are_asked_and_errors_are_kept():
    def fetch(url):
        if "bad" in url:
            raise OSError("timed out")
        return {"name": "r2-domecam1", "temp_c": 41.5}, 12
    cams = {"cam1": {"source": "http://good:81/stream"}, "usb": {"source": "/dev/video0"},
            "cam2": {"source": "http://bad:81/stream"}}
    out = domecams_payload(cams, fetch)["cameras"]
    assert [c["name"] for c in out] == ["cam1", "cam2"]
    assert out[0]["status"]["temp_c"] == 41.5 and out[0]["ms"] == 12
    assert out[1]["error"] == "timed out" and "status" not in out[1]


def test_no_cameras():
    assert domecams_payload({}) == {"cameras": []}
    assert domecams_payload(None) == {"cameras": []}
