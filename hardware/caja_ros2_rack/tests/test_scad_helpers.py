# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The collision helper: overlap is a collision, faces that only touch are not."""
from scad import is_empty


def test_touching_faces_are_not_a_collision():
    assert is_empty("check_selftest", {"gap": 0})


def test_overlap_is_a_collision():
    assert not is_empty("check_selftest", {"gap": -0.5})


def test_apart_is_empty():
    assert is_empty("check_selftest", {"gap": 1})


def test_two_separate_touches_are_not_a_collision():
    assert is_empty("check_selftest_two_touches")


def test_volume_reads_binary_stl(tmp_path):
    import struct
    from scad import stl_volume
    # unit cube, 12 triangles, binary
    v = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
    f = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    data = b"\0" * 80 + struct.pack("<I", len(f))
    for t in f:
        data += struct.pack("<12fH", 0, 0, 0, *v[t[0]], *v[t[1]], *v[t[2]], 0)
    p = tmp_path / "c.stl"
    p.write_bytes(data)
    assert abs(stl_volume(p)) == __import__("pytest").approx(1.0)
