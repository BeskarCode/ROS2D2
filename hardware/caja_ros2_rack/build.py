# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Export the rack box (option C): STLs in print orientation and the 4-colour main face as 3MF.

    python -I hardware/caja_ros2_rack/build.py

Same tools as the first box (hardware/caja_ros2/build.py), other parts.
"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("build_ros2", HERE.parent / "caja_ros2" / "build.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
base.SCAD = HERE / "caja_rack.scad"

LOGO_PARTS = ["logo_marino", "logo_azul", "logo_gris"]
PRINT_PARTS = ["pared", *LOGO_PARTS, "pared_monocolor", "pulsador", "base", "tapa", "marco_pi4", "marco_pi5", "prueba_luz"]
write_3mf = base.write_3mf


def build(out_dir=HERE):
    out_dir = pathlib.Path(out_dir)
    (out_dir / "stl").mkdir(parents=True, exist_ok=True)
    written = []
    for p in PRINT_PARTS:
        f = out_dir / "stl" / f"{p}.stl"
        base.openscad(f, p)
        written.append(f)
        print("ok", f.name, flush=True)
    face = {n: out_dir / "stl" / f"{n}.stl" for n in ("pared", *LOGO_PARTS)}
    for name, bambu in (("pared_multicolor.3mf", False), ("pared_multicolor_bambu.3mf", True)):
        f = out_dir / "stl" / name
        write_3mf(face, f, bambu=bambu)
        written.append(f)
        print("ok", name, flush=True)
    return written


if __name__ == "__main__":
    build(*sys.argv[1:2])
