# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The hardware list (fasteners.scad) is the BOM, the drawings in the assembly guide and a check
that every screw goes where the model has a hole for it: through clearance holes and into
inserts, never into solid plastic (a screw too long for its insert bottoms out = collision)."""
import pytest

from scad import echo_values, is_empty

EXPECTED = {
    "ins_m3": 14,         # 4 Pico columns, 2 front tabs, 2 top tabs, 4 shell bosses, 2 converter bosses
    "m3x8_flat": 8,       # 2 front tabs from below, 4 shell sides, 2 roof
    "m3x6_pan": 4,        # Pico board
    "m3x6_cyl": 2,        # converter (its ears are 1.6 mm thick)
    "m3x10_flat": 2,      # XT60E-F
    "nut_m3": 2,          # XT60E-F
    "m25x6": 4,           # Pi
    "m4x12": 4,           # ears -> R2
}


def test_bom_counts():
    v = echo_values("echo_bom")
    assert {k: v[k] for k in EXPECTED} == EXPECTED


@pytest.mark.parametrize("kind", ["m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_flat", "m25x6"])
def test_screws_only_go_through_holes(kind):
    assert is_empty("check_screws_vs_parts", {"kind": kind})


def test_inserts_sit_in_their_holes():
    assert is_empty("check_screws_vs_parts", {"kind": "ins_m3"})


def test_every_insert_has_its_screw():
    # each insert is reached by a screw shaft (screw tip inside the insert's length)
    assert echo_values("echo_bom")["inserts_without_screw"] == 0
