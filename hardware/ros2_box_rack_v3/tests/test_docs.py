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
    assert rows == dict(collections.Counter(f[0] for f in table)) and rows["ins_m3"] == 34 and rows["ins_m25"] == 4


def test_eight_steps_and_the_optional_ninth_both_languages():
    assert [s["n"] for s in STEPS] == list(range(1, 10))      # 9: optional fan and IMU, with its own hardware
    assert STEPS[-1]["es"]["hw"] and STEPS[-1]["en"]["hw"]
    for s in STEPS:
        assert s["es"]["text"] and s["en"]["text"]


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    for n in range(1, 10):
        assert f"assembly/img/step{n}.png" in md
    assert f"wiring_{lang}.svg" in md and f"connectors_{lang}.svg" in md
    assert "wall_multicolor_bambu.3mf" in md and "34× " in md and "frame_pi5.stl" in md
    assert f"scale_{lang}.svg" in md and "github.com/BeskarCode/ROS2D2/tree/main/hardware/ros2_box_rack_v3" in md


# the LED face and the optional light-pipe piece
LIGHT = {"es": ["wall_led_multicolor_bambu.3mf", "wall_led_monocolor.stl", "led_lenses.stl",
                "PETG transparente", "lentilla", "a ras", "lija la punta", "J4", "sin tornillos", "sin balancearse"],
         "en": ["wall_led_multicolor_bambu.3mf", "wall_led_monocolor.stl", "led_lenses.stl",
                "clear PETG", "lens", "flush", "sand its tip", "J4", "without screws", "without rocking"]}


@pytest.mark.parametrize("lang,name", [("es", "MONTAJE.md"), ("en", "ASSEMBLY.md")])
def test_guide_has_the_led_face_and_the_light_pipes(tmp_path, table, lang, name):
    write_guide(lang, table, tmp_path / name)
    md = (tmp_path / name).read_text(encoding="utf8")
    for words in LIGHT[lang]:
        assert words in md, words


@pytest.mark.parametrize("name,words", [("README_es.md", ["translúcido", "tubo", "no_ams/wall_led_no_ams.stl", "PRINT_GUIDE.md"]),
                                        ("README.md", ["translucent", "tube", "no_ams/wall_led_no_ams.stl", "PRINT_GUIDE.md"])])
def test_readme_has_the_led_face(name, words):
    md = (pathlib.Path(__file__).resolve().parent.parent / name).read_text(encoding="utf8")
    for w in ["wall_led_multicolor_bambu.3mf", "led_lenses.stl", "assembly/img/assembled_led.png", *words]:
        assert w in md, w
    assert "guias_luz" not in md and "prueba_luz" not in md      # the old light-pipe piece is gone


def test_led_version_parts_go_in_their_own_folder(tmp_path):
    import build
    led = ["wall_led", "wall_led_monocolor", "logo_navy_led", "logo_blue_led", "logo_grey_led", "led_lenses"]
    for p in led:
        assert build.stl_path(tmp_path, p) == tmp_path / "stl" / "leds" / f"{p}.stl"
    assert build.stl_path(tmp_path, "wall") == tmp_path / "stl" / "wall.stl"
    assert build.face_path(tmp_path, "wall_led_multicolor_bambu.3mf") == tmp_path / "stl" / "leds" / "wall_led_multicolor_bambu.3mf"
    assert build.face_path(tmp_path, "wall_multicolor.3mf") == tmp_path / "stl" / "wall_multicolor.3mf"


@pytest.mark.parametrize("name,words", [("README_es.md", ["62 × 95 × 145 mm", "ear.stl", "ear_blank.stl", "13 lentillas", "1,4 mm"]),
                                        ("README.md", ["62 × 95 × 145 mm", "ear.stl", "ear_blank.stl", "13 lenses", "1.4 mm"])])
def test_readme_is_the_v3_box(name, words):
    md = (pathlib.Path(__file__).resolve().parent.parent / name).read_text(encoding="utf8")
    for w in words:
        assert w in md, w
    assert "78 ×" not in md and "orejetas." not in md and "acodado lateral" not in md
