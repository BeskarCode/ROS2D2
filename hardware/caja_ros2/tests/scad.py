# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Helpers that drive the OpenSCAD CLI for the enclosure tests.

    run_scad("frontal")                      -> Path of an STL of that part
    is_empty("check_frontal_vs_ghosts")      -> True when the part renders to nothing
    echo_values("echo_layout")               -> {"W": 107.0, "oled_view_center": [72.0, 26.5], ...}
"""
import ast
import hashlib
import os
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
SCAD = HERE / "caja_ros2.scad"
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
CACHE = pathlib.Path(tempfile.gettempdir()) / "caja_ros2_tests"


def _defs_args(part, defs):
    args = ["-D", f'part="{part}"']
    for k, v in (defs or {}).items():
        args += ["-D", f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"]
    return args


def _sources_hash():
    h = hashlib.sha1()
    for p in sorted(HERE.glob("*.scad")) + sorted((HERE / "logo").glob("*.svg")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def _run(part, defs, ext):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(repr((part, sorted((defs or {}).items()), ext, _sources_hash())).encode()).hexdigest()[:16]
    out = CACHE / f"{part}-{key}.{ext}"
    log = out.with_suffix(".log")
    if not SCAD.exists():
        raise FileNotFoundError(SCAD)
    if not log.exists():
        r = subprocess.run([OPENSCAD, "-o", str(out), *_defs_args(part, defs), str(SCAD)],
                           capture_output=True, text=True, timeout=1800)
        log.write_text(r.stdout + r.stderr, encoding="utf8")
        both = r.stdout + r.stderr
        empty = "top level object is empty" in both or "No top level geometry" in both
        if "ERROR" in both or "WARNING: Ignoring unknown" in both or (r.returncode and not empty):
            log.unlink()
            raise RuntimeError(f"OpenSCAD failed for {part}:\n{both[-3000:]}")
    return out, log.read_text(encoding="utf8")


def run_scad(part, defs=None, out_ext="stl"):
    out, text = _run(part, defs, out_ext)
    if not out.exists():
        raise RuntimeError(f"OpenSCAD wrote nothing for {part}:\n{text[-3000:]}")
    return out


def stl_bbox(path):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    data = pathlib.Path(path).read_bytes()
    if data[:5] == b"solid":
        for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data):
            for i in range(3):
                v = float(m.group(i + 1))
                lo[i] = min(lo[i], v)
                hi[i] = max(hi[i], v)
    else:
        import struct
        n = struct.unpack_from("<I", data, 80)[0]
        for t in range(n):
            vals = struct.unpack_from("<12f", data, 84 + t * 50)
            for k in range(3):
                for i in range(3):
                    v = vals[3 + k * 3 + i]
                    lo[i] = min(lo[i], v)
                    hi[i] = max(hi[i], v)
    if lo[0] == float("inf"):
        raise ValueError(f"empty STL {path}")
    return tuple(lo), tuple(hi)


def is_empty(part, defs=None):
    out, text = _run(part, defs, "stl")
    if "top level object is empty" in text or "No top level geometry" in text:
        return True
    if not out.exists() or out.stat().st_size < 200:
        return True
    lo, hi = stl_bbox(out)                     # faces that only touch leave a flat sliver
    return min(h - l for l, h in zip(lo, hi)) < 0.01


def echo_values(part, defs=None):
    out, text = _run(part, defs, "echo")
    src = out.read_text(encoding="utf8") if out.exists() else text
    vals = {}
    for m in re.finditer(r'ECHO: "([^"]+)", (.+)', src):
        vals[m.group(1)] = ast.literal_eval(m.group(2).strip())
    return vals
