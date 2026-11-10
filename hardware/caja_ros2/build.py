# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Export everything the printer needs from caja_ros2.scad.

    python -I hardware/caja_ros2/build.py

Writes stl/{frontal,logo_negro,logo_azul,base,carcasa}.stl (each in its print orientation),
stl/frontal_multicolor.3mf (the front and its two logo inlays as ONE object with 3 parts: in
Bambu Studio give each part its filament) and renders/*.png.
"""
import os
import pathlib
import re
import subprocess
import sys
import zipfile
from xml.sax.saxutils import quoteattr

HERE = pathlib.Path(__file__).resolve().parent
SCAD = HERE / "caja_ros2.scad"
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
PRINT_PARTS = ["frontal", "logo_negro", "logo_azul", "frontal_monocolor", "base", "carcasa"]
# name -> camera (translate x,y,z, rotate x,y,z, distance)
RENDERS = {
    "montaje": "53,66,60,62,0,35,480",
    "trasera": "53,66,60,62,0,215,480",
    "frontal": "53.5,0,62.5,90,0,0,330",
    "base": "53,66,60,55,0,25,420",
    "carcasa": "53,66,60,55,0,25,420",
}


def openscad(out, part, extra=()):
    r = subprocess.run([OPENSCAD, "-o", str(out), "-D", f'part="{part}"', *extra, str(SCAD)],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode or "ERROR" in r.stdout + r.stderr:
        raise RuntimeError(f"OpenSCAD failed for {part}:\n{(r.stdout + r.stderr)[-2000:]}")


def _read_stl(path):
    data = pathlib.Path(path).read_bytes()
    pts = [tuple(m) for m in re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
    index, verts, tris = {}, [], []
    for i in range(0, len(pts) - 2, 3):
        t = []
        for p in pts[i:i + 3]:
            if p not in index:
                index[p] = len(verts)
                verts.append(p)
            t.append(index[p])
        if len(set(t)) == 3:
            tris.append(t)
    return verts, tris


def write_3mf(parts, path):
    """One object made of the given STLs as components (same transform), named after the keys."""
    objs = []
    for oid, (name, stl) in enumerate(parts.items(), 1):
        verts, tris = _read_stl(stl)
        v = "".join(f'<vertex x="{x.decode()}" y="{y.decode()}" z="{z.decode()}"/>' for x, y, z in verts)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        objs.append(f'<object id="{oid}" name={quoteattr(name)} type="model"><mesh><vertices>{v}</vertices>'
                    f'<triangles>{t}</triangles></mesh></object>')
    cid = len(parts) + 1
    comps = "".join(f'<component objectid="{i}"/>' for i in range(1, cid))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objs)}<object id="{cid}" name="frontal_multicolor" type="model">'
             f'<components>{comps}</components></object></resources>'
             f'<build><item objectid="{cid}"/></build></model>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def build(out_dir=HERE, renders=True):
    out_dir = pathlib.Path(out_dir)
    (out_dir / "stl").mkdir(parents=True, exist_ok=True)
    written = []
    for p in PRINT_PARTS:
        f = out_dir / "stl" / f"{p}.stl"
        openscad(f, p)
        written.append(f)
        print("ok", f.name, flush=True)
    f = out_dir / "stl" / "frontal_multicolor.3mf"
    write_3mf({n: out_dir / "stl" / f"{n}.stl" for n in ("frontal", "logo_negro", "logo_azul")}, f)
    written.append(f)
    if renders:
        (out_dir / "renders").mkdir(exist_ok=True)
        for name, cam in RENDERS.items():
            f = out_dir / "renders" / f"{name}.png"
            part = {"trasera": "montaje", "frontal": "vista_frontal", "base": "base_montada",
                    "carcasa": "carcasa_montada"}.get(name, name)
            openscad(f, part, ["--imgsize=1400,1050", f"--camera={cam}", "--colorscheme=Tomorrow"])
            written.append(f)
            print("ok", f.name, flush=True)
    return written


if __name__ == "__main__":
    build(*sys.argv[1:2])
