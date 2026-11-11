# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""build_docs.py: the assembly guide (ES + EN) and its BOM come from the hardware table."""
import collections

import pytest

from build_docs import STEPS, bom, fastener_table, write_guide


@pytest.fixture(scope="module")
def table():
    return fastener_table()


def test_table_has_every_fastener(table):
    c = collections.Counter(f[0] for f in table)
    assert c["ins_m3"] == 14 and c["m3x8_flat"] == 8 and c["m25x6"] == 4


def test_bom_totals_match_the_table(table):
    rows = {r["kind"]: r["qty"] for r in bom(table)}
    assert rows == dict(collections.Counter(f[0] for f in table))


def test_eight_steps_in_both_languages():
    assert [s["n"] for s in STEPS] == list(range(1, 9))
    for s in STEPS:
        assert s["es"]["title"] and s["en"]["title"] and s["es"]["text"] and s["en"]["text"]


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide_lists_each_steps_hardware(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    for n in range(1, 9):
        assert f"montaje/img/paso{n}.png" in md
    assert "4× M3 × 6" in md          # step 5, Pico board screws
    assert "14× " in md               # the inserts, in the BOM


@pytest.mark.parametrize("lang,words", [
    ("es", ["Batería 24 V", "Interruptor", "Convertidor", "USB-C", "J1", "US1–US5", "VL1–VL4", "Mega", "Lidar"]),
    ("en", ["24 V battery", "Switch", "Converter", "USB-C", "J1", "US1–US5", "VL1–VL4", "Mega", "Lidar"])])
def test_wiring_diagram_labels(lang, words):
    from build_docs import wiring_svg
    svg = wiring_svg(lang)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for w in words:
        assert w in svg, w


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide_shows_the_wiring(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    assert f"montaje/img/conexiones_{lang}.svg" in md
    assert f"montaje/img/conectores_{lang}.svg" in md          # which way the angled plugs go


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide_links_the_repo_and_shows_the_size(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    assert "https://github.com/BeskarCode/ROS2D2/tree/main/hardware/caja_ros2" in md   # the PDF may be old
    assert f"montaje/img/escala_{lang}.svg" in md                                      # R2 and the box, same scale


@pytest.mark.parametrize("lang", ["es", "en"])
def test_pdf_and_guide_carry_the_logos(tmp_path, table, lang):
    from build_docs import write_html
    h = tmp_path / "g.html"
    write_html(lang, table, h)
    html = h.read_text(encoding="utf8")
    assert "ros2d2-logo.png" in html and "astromech-spain-logo-circular.png" in html   # the one readable on white
    write_guide(lang, table, tmp_path / "g.md")
    md = (tmp_path / "g.md").read_text(encoding="utf8")
    assert "../../media/ros2d2-logo.png" in md
