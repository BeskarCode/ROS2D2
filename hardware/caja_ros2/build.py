# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Export everything the printer needs from caja_ros2.scad.

    python -I hardware/caja_ros2/build.py

Writes stl/{frontal,logo_marino,logo_azul,logo_gris,base,carcasa}.stl (each in its print orientation),
stl/frontal_multicolor.3mf (the front and its three logo inlays as ONE object with 4 parts: in
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
LOGO_PARTS = ["logo_marino", "logo_azul", "logo_gris"]
PRINT_PARTS = ["frontal", *LOGO_PARTS, "frontal_monocolor", "pulsador", "base", "carcasa"]
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


def write_3mf(parts, path, bambu=False):
    """One object made of the given STLs as components (same transform), named after the keys.
    bambu=True: also Bambu Studio's project metadata, so it opens as one object whose parts already
    have filaments 1, 2, 3, 4 (in the order of parts) and sits in the middle of the plate."""
    objs = []
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for oid, (name, stl) in enumerate(parts.items(), 1):
        verts, tris = _read_stl(stl)
        for p in verts:
            for i in range(3):
                lo[i] = min(lo[i], float(p[i])); hi[i] = max(hi[i], float(p[i]))
        v = "".join(f'<vertex x="{x.decode()}" y="{y.decode()}" z="{z.decode()}"/>' for x, y, z in verts)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        objs.append(f'<object id="{oid}" name={quoteattr(name)} type="model"><mesh><vertices>{v}</vertices>'
                    f'<triangles>{t}</triangles></mesh></object>')
    cid = len(parts) + 1
    comps = "".join(f'<component objectid="{i}"/>' for i in range(1, cid))
    if bambu:
        tx, ty, tz = 128 - (lo[0] + hi[0]) / 2, 128 - (lo[1] + hi[1]) / 2, -lo[2]
        head = ('<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
                'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
                '<metadata name="Application">BambuStudio-01.09.00.70</metadata>'
                '<metadata name="BambuStudio:3mfVersion">1</metadata>'
                '<metadata name="Title">ROS2D2 caja - frontal multicolor</metadata>')
        item = f'<item objectid="{cid}" transform="1 0 0 0 1 0 0 0 1 {tx:.3f} {ty:.3f} {tz:.3f}" printable="1"/>'
    else:
        head = '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        item = f'<item objectid="{cid}"/>'
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n' + head +
             f'<resources>{"".join(objs)}<object id="{cid}" name="frontal_multicolor" type="model">'
             f'<components>{comps}</components></object></resources>'
             f'<build>{item}</build></model>')
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
        if bambu:
            ident = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
            prt = "".join(
                f'<part id="{i}" subtype="normal_part"><metadata key="name" value={quoteattr(n)}/>'
                f'<metadata key="matrix" value="{ident}"/><metadata key="extruder" value="{i}"/></part>'
                for i, n in enumerate(parts, 1))
            cfg = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>'
                   f'<object id="{cid}"><metadata key="name" value="frontal_multicolor"/>'
                   f'<metadata key="extruder" value="1"/>{prt}</object>'
                   '<plate><metadata key="plater_id" value="1"/><metadata key="plater_name" value=""/>'
                   '<metadata key="locked" value="false"/>'
                   f'<model_instance><metadata key="object_id" value="{cid}"/>'
                   '<metadata key="instance_id" value="0"/><metadata key="identify_id" value="101"/>'
                   '</model_instance></plate></config>\n')
            z.writestr("Metadata/model_settings.config", cfg)


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
    front = {n: out_dir / "stl" / f"{n}.stl" for n in ("frontal", *LOGO_PARTS)}
    write_3mf(front, f)
    written.append(f)
    f = out_dir / "stl" / "frontal_multicolor_bambu.3mf"
    write_3mf(front, f, bambu=True)
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
