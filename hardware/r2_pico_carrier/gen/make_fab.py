# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The ordering packages for the carrier board, from the routed r2_pico_carrier.kicad_pcb:

  jlcpcb/  gerber.zip, bom.csv (Comment, Designator, Footprint, LCSC Part #), cpl.csv
  pcbway/  gerber.zip, bom.csv (Item #, Designator, Qty, Manufacturer, Mfg Part #, ...), centroid.csv

Both assemble the top side only (everything is on top); the M3 holes are not parts.

    $KPY hardware/r2_pico_carrier/gen/make_fab.py
"""
import csv
import os
import shutil
import subprocess
import tempfile
import zipfile

from parts import MAKER, PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PCB = os.path.join(ROOT, "r2_pico_carrier.kicad_pcb")
CLI = os.environ.get("KICAD_CLI", r"C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe")
# JLCPCB library models that sit turned against KiCad's: degrees added in their CPL only
JLC_ROTATION = {"C2905423": 90, "C80799": 270}     # 1x20 socket; PCA9517A TSSOP-8
# Single parts their engineer turned in the placement review (SMT026102861860, 29 Oct 2026): the
# vertical 1k next to the VL LEDs, pad 1 at the top. A resistor either way round, but sent as they
# left it the review has nothing to change.
JLC_REF_ROTATION = {"R31": 180, "R32": 180, "R33": 180, "R34": 180}
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"


def cli(*args):
    subprocess.run([CLI, *args], check=True, capture_output=True)


def gerbers(zip_path):
    tmp = tempfile.mkdtemp()
    cli("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "-o", tmp + os.sep, PCB)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", tmp + os.sep, PCB)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(tmp)):
            z.write(os.path.join(tmp, name), name)
    shutil.rmtree(tmp)


def positions():
    """[(ref, x, y, rotation)] of the assembled parts in mm, from the bottom-left corner, y up.
    The position is the centre of the part's pads: fabs place by the part's centre, while
    KiCad anchors a through-hole part on its pin 1."""
    import pcbnew
    board = pcbnew.LoadBoard(PCB)
    origin = board.GetDesignSettings().GetAuxOrigin()       # bottom-left corner (make_pcb.py)
    ox, oy = pcbnew.ToMM(origin.x), pcbnew.ToMM(origin.y)
    out = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in PARTS or ref.startswith("H"):
            continue
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in fp.Pads()]
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in fp.Pads()]
        x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        out.append((ref, x - ox, oy - y, fp.GetOrientationDegrees() % 360))
    return sorted(out)


def groups():
    """{lcsc: [refs]} for the assembled parts, in reference order."""
    g = {}
    for ref, part in sorted(PARTS.items(), key=lambda kv: (kv[0].rstrip("0123456789"), int("0" + "".join(c for c in kv[0] if c.isdigit())))):
        if not ref.startswith("H"):
            g.setdefault(part.lcsc, []).append(ref)
    return g


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    pos = positions()
    for fab in ("jlcpcb", "pcbway"):
        os.makedirs(os.path.join(ROOT, fab), exist_ok=True)
        gerbers(os.path.join(ROOT, fab, "gerber.zip"))
    g = groups()
    write_csv(os.path.join(ROOT, "jlcpcb", "bom.csv"), ["Comment", "Designator", "Footprint", "LCSC Part #"],
              [[PARTS[refs[0]].value, ",".join(refs), PARTS[refs[0]].footprint.split(":")[1], lcsc]
               for lcsc, refs in g.items()])
    write_csv(os.path.join(ROOT, "jlcpcb", "cpl.csv"), ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
              [[r, f"{x:.3f}mm", f"{y:.3f}mm", "Top", f"{(rot + JLC_ROTATION.get(PARTS[r].lcsc, 0) + JLC_REF_ROTATION.get(r, 0)) % 360:.1f}"]
               for r, x, y, rot in pos])
    rows = []
    for i, (lcsc, refs) in enumerate(g.items(), 1):
        maker, mpn, kind = MAKER[lcsc]
        part = PARTS[refs[0]]
        note = f"LCSC {lcsc}"
        if "J2" in refs:
            note += ". J2 is the OLED header: the OLED module is not supplied, it is soldered on later."
        rows.append([i, ",".join(refs), len(refs), maker, mpn, part.value, part.footprint.split(":")[1], kind,
                     note])
    write_csv(os.path.join(ROOT, "pcbway", "bom.csv"),
              ["Item #", "Designator", "Qty", "Manufacturer", "Mfg Part #", "Description / Value",
               "Package/Footprint", "Type", "Your Instructions / Notes"], rows)
    write_csv(os.path.join(ROOT, "pcbway", "centroid.csv"), ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
              [[r, f"{x:.3f}", f"{y:.3f}", "Top", f"{rot:.1f}"] for r, x, y, rot in pos])
    print("jlcpcb/ and pcbway/ written:", len(g), "BOM lines,", len(pos), "placed parts")


if __name__ == "__main__":
    main()
