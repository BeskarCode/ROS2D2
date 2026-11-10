# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""build.py: the STLs to print, the front as a multi-part 3MF for Bambu Studio + AMS, renders."""
import zipfile

import pytest

from build import PRINT_PARTS, build, write_3mf
from scad import stl_bbox

TRIANGLE = b"""solid t
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 1 0 0
vertex 0 1 0
endloop
endfacet
endsolid t
"""


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("build")
    build(d, renders=False)
    return d


def test_build_outputs_exist_and_not_empty(out):
    for name in ["frontal", "logo_negro", "logo_azul", "base", "carcasa"]:
        assert (out / "stl" / f"{name}.stl").stat().st_size > 1000


def test_3mf_has_three_named_parts(tmp_path):
    parts = {}
    for n in ("frontal", "logo_negro", "logo_azul"):
        parts[n] = tmp_path / f"{n}.stl"
        parts[n].write_bytes(TRIANGLE)
    write_3mf(parts, tmp_path / "f.3mf")
    with zipfile.ZipFile(tmp_path / "f.3mf") as z:
        model = z.read("3D/3dmodel.model").decode()
        assert "[Content_Types].xml" in z.namelist() and "_rels/.rels" in z.namelist()
    assert model.count("<object ") == 4                  # 3 meshes + 1 container
    assert model.count("<component ") == 3
    for n in ("frontal", "logo_negro", "logo_azul"):
        assert f'name="{n}"' in model


def test_build_writes_the_front_3mf(out):
    with zipfile.ZipFile(out / "stl" / "frontal_multicolor.3mf") as z:
        assert z.read("3D/3dmodel.model").count(b"<triangle ") > 1000


@pytest.mark.parametrize("name", PRINT_PARTS)
def test_every_part_fits_p1s_bed_and_sits_on_it(out, name):
    lo, hi = stl_bbox(out / "stl" / f"{name}.stl")
    assert all(h - l <= 250 for l, h in zip(lo, hi))
    assert lo[2] == pytest.approx(0, abs=0.01)


def test_build_writes_the_monocolor_front(out):
    assert (out / "stl" / "frontal_monocolor.stl").stat().st_size > 1000


def test_build_writes_the_push_rod(out):
    assert (out / "stl" / "pulsador.stl").stat().st_size > 1000
