# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The rack box's guide (ES + EN): 8 steps, BOM from this box's hardware table, wiring and angled plugs."""
import collections
import pathlib

import pytest

from build_docs import STEPS, bom, fastener_table, write_guide


@pytest.fixture(scope="module")
def table():
    return fastener_table()


def test_bom_matches_the_table(table):
    rows = {r["kind"]: r["qty"] for r in bom(table)}
    assert rows == dict(collections.Counter(f[0] for f in table)) and rows["ins_m3"] == 19 and rows["ins_m25"] == 4


def test_eight_steps_both_languages():
    assert [s["n"] for s in STEPS] == list(range(1, 9))
    for s in STEPS:
        assert s["es"]["text"] and s["en"]["text"]


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    for n in range(1, 9):
        assert f"montaje/img/paso{n}.png" in md
    assert f"conexiones_{lang}.svg" in md and f"conectores_{lang}.svg" in md
    assert "pared_multicolor_bambu.3mf" in md and "19× " in md and "marco_pi5.stl" in md
    assert f"escala_{lang}.svg" in md and "github.com/BeskarCode/ROS2D2/tree/main/hardware/caja_ros2_rack" in md


# the LED face and the optional light-pipe piece
LIGHT = {"es": ["pared_led_multicolor_bambu.3mf", "pared_led_monocolor.stl", "guias_luz.stl", "prueba_luz.stl",
                "PETG transparente", "opcional", "antes de colgar la placa", "lija la punta", "J4",
                "sin tornillos", "sin balancearse", "Para sacarla"],
         "en": ["pared_led_multicolor_bambu.3mf", "pared_led_monocolor.stl", "guias_luz.stl", "prueba_luz.stl",
                "clear PETG", "optional", "before hanging the board", "sand its tip", "J4",
                "without screws", "without rocking", "To take it out"]}


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide_has_the_led_face_and_the_light_pipes(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    for words in LIGHT[lang]:
        assert words in md, words


def test_readme_has_the_led_face():
    md = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf8")
    for words in ["pared_led_multicolor_bambu.3mf", "guias_luz.stl", "prueba_luz.stl", "translúcido", "opcional",
                  "montaje/img/montada_led.png"]:
        assert words in md, words
