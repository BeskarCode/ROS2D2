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
    """[(ref, x, y, rotation)] of the assembled parts, from KiCad, in mm (y up, as fabs want)."""
    tmp = os.path.join(tempfile.mkdtemp(), "pos.csv")
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front",
        "--use-drill-file-origin", "-o", tmp, PCB)
    with open(tmp, encoding="utf-8", newline="") as f:
        out = [(r["Ref"], float(r["PosX"]), float(r["PosY"]), float(r["Rot"])) for r in csv.DictReader(f)]
    return [p for p in out if p[0] in PARTS and not p[0].startswith("H")]


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
              [[r, f"{x:.3f}mm", f"{y:.3f}mm", "Top", f"{rot:.1f}"] for r, x, y, rot in pos])
    rows = []
    for i, (lcsc, refs) in enumerate(g.items(), 1):
        maker, mpn, kind = MAKER[lcsc]
        part = PARTS[refs[0]]
        note = f"LCSC {lcsc}"
        if refs == ["J2"]:
            note += (". OLED module: solder it flat, screen up, over its silkscreen outline, on a 4-pin "
                     "2.54 mm male header (pins GND VCC SCL SDA match the board).")
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
