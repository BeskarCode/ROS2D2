from r2_camera.source import is_file, is_network, parse_source


def test_index_becomes_int():
    assert parse_source("0") == 0
    assert parse_source(" 2 ") == 2


def test_paths_and_urls_stay_strings():
    assert parse_source("/dev/video0") == "/dev/video0"
    assert parse_source("http://192.168.68.150:81/stream") == "http://192.168.68.150:81/stream"


def test_is_network():
    assert is_network("http://cam/stream")
    assert is_network("rtsp://cam/live")
    assert not is_network("/dev/video0")
    assert not is_network(0)


def test_is_file(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    assert is_file(str(video))
    assert not is_file(str(tmp_path / "missing.mp4"))
    assert not is_file("/dev/video0")
    assert not is_file("http://cam/stream")
    assert not is_file(0)


V4L2 = """ioctl: VIDIOC_ENUM_FMT
	Type: Video Capture

	[0]: 'MJPG' (Motion-JPEG, compressed)
		Size: Discrete 1280x720
			Interval: Discrete 0.033s (30.000 fps)
		Size: Discrete 640x480
			Interval: Discrete 0.033s (30.000 fps)
			Interval: Discrete 0.067s (15.000 fps)
		Size: Discrete 1280x720
			Interval: Discrete 0.033s (30.000 fps)
	[1]: 'YUYV' (YUYV 4:2:2)
		Size: Discrete 1280x720
			Interval: Discrete 0.100s (10.000 fps)
"""


def test_parse_v4l2_formats():
    from r2_camera.source import parse_v4l2_formats
    modes = parse_v4l2_formats(V4L2)
    assert modes["MJPG"] == [(1280, 720, 30.0), (640, 480, 30.0)]     # no repeats, best fps
    assert modes["YUYV"] == [(1280, 720, 10.0)]
