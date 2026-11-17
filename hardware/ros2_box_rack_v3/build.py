# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Export the rack box: STLs in print orientation and the 4-colour main face as 3MF.

    python -I hardware/ros2_box_rack_v3/build.py

Shared export tools live in build_core.py.
"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("build_ros2", HERE / "build_core.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
base.SCAD = HERE / "rack_box.scad"

LOGO_PARTS = ["logo_navy", "logo_blue", "logo_grey"]
LOGO_LED_PARTS = ["logo_navy_led", "logo_blue_led", "logo_grey_led"]
PRINT_PARTS = ["wall", *LOGO_PARTS, "wall_monocolor", "push_rod", "base", "shell", "frame_pi4", "frame_pi5",
               "wall_led", *LOGO_LED_PARTS, "wall_led_monocolor", "led_lenses"]
# the LED face without AMS: deep pockets, the fillings printed apart (stl/no_ams/; same lenses as leds/)
NOAMS_DIR = "no_ams"
NOAMS_PARTS = ["wall_led_no_ams", "inlay_navy", "inlay_blue", "inlay_grey"]
PRINT_PARTS += NOAMS_PARTS
# the removable ears (4 + 1 spare) and the blanks for the unused sites (4)
PRINT_PARTS += ["ear", "ear_blank"]
# the LED version's parts live in their own folder, stl/leds/
LED_DIR = "leds"
LED_PARTS = {"wall_led", *LOGO_LED_PARTS, "wall_led_monocolor", "led_lenses"}


def stl_path(out_dir, part):
    out_dir = pathlib.Path(out_dir) / "stl"
    if part in NOAMS_PARTS:
        return out_dir / NOAMS_DIR / f"{part}.stl"
    return (out_dir / LED_DIR if part in LED_PARTS else out_dir) / f"{part}.stl"


def face_path(out_dir, name):
    out_dir = pathlib.Path(out_dir) / "stl"
    return (out_dir / LED_DIR if name.startswith("wall_led") else out_dir) / name


# the multicolour main faces: today's, and the LED face (same colour bodies, other STLs)
FACES = {"wall_multicolor": ("wall", *LOGO_PARTS), "wall_led_multicolor": ("wall_led", *LOGO_LED_PARTS)}
write_3mf = base.write_3mf


def build(out_dir=HERE):
    out_dir = pathlib.Path(out_dir)
    (out_dir / "stl" / LED_DIR).mkdir(parents=True, exist_ok=True)
    (out_dir / "stl" / NOAMS_DIR).mkdir(parents=True, exist_ok=True)
    written = []
    for p in PRINT_PARTS:
        f = stl_path(out_dir, p)
        base.openscad(f, p)
        written.append(f)
        print("ok", f.name, flush=True)
    written += write_faces(out_dir)
    return written


def write_faces(out_dir=HERE, faces=FACES):
    """The multicolour 3MFs from STLs already in stl/; bodies named as today's (pared, logo_navy, ...)."""
    out_dir = pathlib.Path(out_dir)
    written = []
    for stem, parts in faces.items():
        face = {key: stl_path(out_dir, p) for key, p in zip(("wall", *LOGO_PARTS), parts)}
        for name, bambu in ((f"{stem}.3mf", False), (f"{stem}_bambu.3mf", True)):
            f = face_path(out_dir, name)
            write_3mf(face, f, bambu=bambu)
            written.append(f)
            print("ok", name, flush=True)
    return written


if __name__ == "__main__":
    build(*sys.argv[1:2])
