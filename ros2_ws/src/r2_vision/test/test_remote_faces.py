# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import cv2
import numpy as np
import pytest

from r2_vision.remote_faces import (control_url, faces_url, iter_lines, marker_raw_json, orient_box,
                                   orient_point, parse_line)

ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
FLIPS = {"h": 1, "v": 0, "both": -1}


def test_faces_url_from_stream():
    assert faces_url("http://r2-domecam1.local:81/stream") == "http://r2-domecam1.local:82/faces"
    assert faces_url("http://192.168.68.109:81/stream") == "http://192.168.68.109:82/faces"
    assert faces_url("/dev/video0") is None


def test_parse_line():
    d = parse_line('{"seq":3,"lat_ms":66,"w":320,"h":240,"faces":[[10,20,30,40,0.91],[1,2,3,4,0.5]]}\n')
    assert d["lat_ms"] == 66 and d["w"] == 320 and d["h"] == 240 and d["rot"] == 0
    assert d["faces"] == [(10, 20, 30, 40, 0.91), (1, 2, 3, 4, 0.5)]


def test_parse_rot():
    assert parse_line('{"lat_ms":5,"w":240,"h":320,"rot":90,"faces":[]}')["rot"] == 90


def test_parse_keepalive_and_garbage():
    assert parse_line("\n") is None
    assert parse_line("busy: another viewer") is None
    assert parse_line('{"faces":[]}') is None


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
@pytest.mark.parametrize("flip", ["none", "h", "v", "both"])
def test_orient_box_matches_the_picture(rotate, flip):
    """Mark a box in a picture, turn the picture like the camera node does: the box moves
    exactly where orient_box says."""
    W, H, box = 32, 24, (5, 3, 7, 4)
    img = np.zeros((H, W), np.uint8)
    x, y, w, h = box
    img[y:y + h, x:x + w] = 255
    if rotate:
        img = cv2.rotate(img, ROTATIONS[rotate])
    if flip != "none":
        img = cv2.flip(img, FLIPS[flip])
    ys, xs = np.nonzero(img)
    expected = (xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1, img.shape[1], img.shape[0])
    assert orient_box(*box, W, H, rotate, flip) == expected


class _Chunked:
    """Hands out the bytes in the pieces the camera sent them, like HTTPResponse.read1."""

    def __init__(self, pieces):
        self.pieces = list(pieces)

    def read1(self, n=-1):
        return self.pieces.pop(0) if self.pieces else b""


def test_iter_lines_gives_each_line_as_soon_as_it_arrives():
    stream = _Chunked([b'{"seq":1}\n', b'\n', b'{"seq":', b'2}\n{"seq":3}\n'])
    lines = iter_lines(stream)
    assert next(lines) == '{"seq":1}'
    assert stream.pieces == [b'\n', b'{"seq":', b'2}\n{"seq":3}\n']   # nothing read ahead
    assert list(lines) == ["", '{"seq":2}', '{"seq":3}']


def test_control_url_from_faces_url():
    assert control_url("http://r2-domecam1.local:82/faces", "rotate", 90) ==         "http://r2-domecam1.local/control?var=rotate&val=90"
    assert control_url("", "rotate", 0) is None


def test_control_url_detect():
    assert control_url("http://r2-domecam1.local:82/faces", "detect", 0) == "http://r2-domecam1.local/control?var=detect&val=0"
    assert control_url("http://r2-domecam1.local:82/faces", "detect", 1) == "http://r2-domecam1.local/control?var=detect&val=1"


def test_parse_marker_line():
    d = parse_line('{"seq":4,"lat_ms":30,"w":320,"h":240,"rot":0,"mode":"color","faces":[],"marker":[0.25,0.5,0.012]}')
    assert d["mode"] == "color" and d["faces"] == [] and d["marker"] == (0.25, 0.5, 0.012)
    d = parse_line('{"seq":5,"lat_ms":30,"w":320,"h":240,"mode":"color","faces":[],"marker":null}')
    assert d["mode"] == "color" and d["marker"] is None


def test_parse_old_line_is_faces():
    d = parse_line('{"seq":3,"lat_ms":66,"w":320,"h":240,"faces":[[10,20,30,40,0.91]]}')
    assert d["mode"] == "faces" and d["marker"] is None


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
@pytest.mark.parametrize("flip", ["none", "h", "v", "both"])
def test_orient_point_matches_orient_box(rotate, flip):
    """The centre of a box turned with orient_box is the point turned with orient_point."""
    W, H, x, y, w, h = 320, 240, 40, 30, 60, 20
    bx, by, bw, bh, ww, hh = orient_box(x, y, w, h, W, H, rotate, flip)
    cx, cy = orient_point((x + w / 2) / W, (y + h / 2) / H, W, H, rotate, flip)
    assert cx == pytest.approx((bx + bw / 2) / ww)
    assert cy == pytest.approx((by + bh / 2) / hh)


def test_marker_raw_json_turns_the_blob():
    import json
    d = parse_line('{"lat_ms":30,"w":320,"h":240,"rot":0,"mode":"color","faces":[],"marker":[0.25,0.5,0.01]}')
    m = json.loads(marker_raw_json(d, 0, "none"))
    assert m == {"seen": True, "cx": 0.25, "cy": 0.5, "area": 0.01, "lat_ms": 30.0}
    m = json.loads(marker_raw_json(d, 0, "h"))
    assert m["cx"] == pytest.approx(0.75)
    d["marker"] = None
    assert json.loads(marker_raw_json(d, 0, "none"))["seen"] is False
