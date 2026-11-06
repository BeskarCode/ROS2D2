# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import cv2
import numpy as np
import pytest

from r2_vision.remote_faces import faces_url, iter_lines, orient_box, parse_line

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
