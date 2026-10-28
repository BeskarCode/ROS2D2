"""The ordering packages made by make_fab.py: JLCPCB (LCSC parts) and PCBWay (maker part numbers)."""
import csv
import os
import zipfile

from parts import PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
LAYERS = ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen", "F_Paste", "B_Paste", "Edge_Cuts")
ASSEMBLED = {r for r, p in PARTS.items() if not r.startswith("H") and not p.dnp}


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def designators(table, column):
    return {d.strip() for r in table for d in r[column].split(",")}


def check_gerbers(zip_path):
    names = zipfile.ZipFile(zip_path).namelist()
    for layer in LAYERS:
        assert any(layer in n for n in names), layer
    assert any(n.endswith(".drl") for n in names)


def test_jlcpcb_package():
    pkg = os.path.join(ROOT, "jlcpcb")
    check_gerbers(os.path.join(pkg, "gerber.zip"))
    bom, cpl = rows(os.path.join(pkg, "bom.csv")), rows(os.path.join(pkg, "cpl.csv"))
    assert list(bom[0]) == ["Comment", "Designator", "Footprint", "LCSC Part #"]
    assert list(cpl[0]) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    assert designators(bom, "Designator") == ASSEMBLED == designators(cpl, "Designator")
    for r in bom:
        refs = [d.strip() for d in r["Designator"].split(",")]
        assert {PARTS[x].lcsc for x in refs} == {r["LCSC Part #"]}
    assert all(r["Layer"] == "Top" for r in cpl)
    # origin at the bottom-left corner: every part inside the 80 x 90 mm board, y up
    assert all(0 < float(r["Mid X"].rstrip("m")) < 80 and 0 < float(r["Mid Y"].rstrip("m")) < 90 for r in cpl)


def test_pcbway_package():
    pkg = os.path.join(ROOT, "pcbway")
    check_gerbers(os.path.join(pkg, "gerber.zip"))
    bom, cpl = rows(os.path.join(pkg, "bom.csv")), rows(os.path.join(pkg, "centroid.csv"))
    assert list(bom[0])[:8] == ["Item #", "Designator", "Qty", "Manufacturer", "Mfg Part #",
                                "Description / Value", "Package/Footprint", "Type"]
    assert designators(bom, "Designator") == ASSEMBLED == designators(cpl, "Designator")
    for r in bom:
        assert r["Mfg Part #"] and r["Manufacturer"], r
        assert int(r["Qty"]) == len(r["Designator"].split(","))
        assert r["Type"] in ("SMD", "THT")


def test_placement_is_the_part_centre():
    """Fabs place a part by its centre: a 1x20 socket's position is halfway along its pins,
    not its pin 1 (KiCad's anchor for through-hole parts)."""
    cpl = {r["Designator"]: r for r in rows(os.path.join(ROOT, "jlcpcb", "cpl.csv"))}
    y = float(cpl["JP1"]["Mid Y"].rstrip("m"))
    pin1_y = 90 - (2.0 + 1.37)                     # board coordinates, y up
    assert abs(y - (pin1_y - 19 * 2.54 / 2)) < 0.05
    x = float(cpl["VL1"]["Mid X"].rstrip("m"))
    assert abs(x - (55.0 + 5 * 2.54 / 2)) < 0.05     # 6 pins from x = 55 to the right


def test_jlcpcb_rotation_offsets():
    """JLCPCB's model of the 1x20 socket lies along x: the CPL turns it 90 deg to stand along
    the Pico's rows (seen in their placement viewer, 27 Oct 2026)."""
    cpl = {r["Designator"]: r for r in rows(os.path.join(ROOT, "jlcpcb", "cpl.csv"))}
    assert float(cpl["JP1"]["Rotation"]) == float(cpl["JP2"]["Rotation"]) == 90.0
    assert float(cpl["US1"]["Rotation"]) == 90.0       # headers were right: unchanged
    # PCA9517A: JLC/EasyEDA's TSSOP-8 model (C80799) has pin 1 bottom-left with pins 1-4 along the
    # bottom; KiCad's VSSOP-8 has pins 1-4 down the left side: +270 (review 28 Oct 2026)
    assert float(cpl["U1"]["Rotation"]) == 270.0
