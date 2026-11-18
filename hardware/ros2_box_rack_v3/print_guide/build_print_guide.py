# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Print guide of the rack box: which files to print and when, one picture per piece (Spanish and English).

    python -I hardware/ros2_box_rack_v3/print_guide/build_print_guide.py [--no-images]

Renders each piece from its STL (run build.py first), writes GUIA_IMPRESION.md/.pdf and PRINT_GUIDE.md/.pdf
(A4, through Edge or Chrome headless).
"""
import html
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
IMG = HERE / "img"
REPO = HERE.parents[2]
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
LOGO_ROS2D2 = REPO / "media" / "ros2d2-logo.png"
LOGO_ASTROMECH = REPO / "media" / "astromech-spain-logo-circular.png"   # the web one is white: lost on paper
REPO_URL = "https://github.com/BeskarCode/ROS2D2/tree/main/hardware/ros2_box_rack_v3"
NAMES = {"es": "GUIA_IMPRESION", "en": "PRINT_GUIDE"}

WALL = "75,0,290"        # the walls stand as mounted, seen from outside
PART = "55,0,25"         # the rest in print orientation

# image -> camera
VIEWS = {"wall_multicolor": WALL, "wall_monocolor": WALL, "wall_led_multicolor": WALL,
         "wall_led_monocolor": WALL, "wall_led_no_ams": WALL, "inlays": WALL,
         "led_lenses": "35,0,25", "base": PART, "shell": "235,0,25", "push_rod": PART,
         "frame_pi4": PART, "frame_pi5": PART, "hdmi_holder": PART, "hdmi_cover": PART,
         "ear": "55,0,35", "ear_blank": PART, "blanks_all": PART}

# --- the guide: every text as (Spanish, English) -----------------------------------------------------------
T = {
    "title": ("Caja ROS2 rack · Guía de impresión", "ROS2 rack box · Print guide"),
    "intro": ("Qué ficheros imprimir y cuándo elegir uno u otro. Solo para la caja rack "
              "(`hardware/ros2_box_rack_v3`). Todos los ficheros están en su carpeta `stl/`.",
              "Which files to print and when to pick one or another. Only for the rack box "
              "(`hardware/ros2_box_rack_v3`). Every file is in its `stl/` folder."),
    "other": ("*In English: [PRINT_GUIDE.md](PRINT_GUIDE.md)*", "*En castellano: [GUIA_IMPRESION.md](GUIA_IMPRESION.md)*"),
    "latest": ("Versión al día", "Up-to-date version"),
    "what": ("Qué imprimir", "What to print"),
    "which": ("¿Qué pared?", "Which wall?"),
    "files": ("Ficheros", "Files"), "is": ("Qué es", "What it is"), "when": ("Cuándo", "When"),
    "how": ("Cómo imprimir", "How to print"),
    "skip": ("Ficheros que no hay que imprimir sueltos", "Files not to print on their own"),
    "skip_head": (("Fichero", "Para qué está"), ("File", "What it is for")),
    "general": ("PETG, capa de 0,2 mm, boquilla de 0,4, sin soportes, salvo donde se indica otra cosa. "
                "Los insertos térmicos y los tornillos son los mismos con cualquier pared: mira la guía de montaje.",
                "PETG, 0.2 mm layers, 0.4 nozzle, no supports, unless said otherwise. The heat-set inserts and "
                "the screws are the same with any wall: see the assembly guide."),
}

CHECKLIST = [
    ("**Siempre:** `base.stl`, `shell.stl` y `push_rod.stl`.", "**Always:** `base.stl`, `shell.stl` and `push_rod.stl`."),
    ("**Una pared principal** de las cinco opciones (tabla de abajo).",
     "**One main wall** out of the five options (table below)."),
    ("**Lentillas** `leds/led_lenses.stl`, solo si la pared que eliges es con LEDs.",
     "**Lenses** `leds/led_lenses.stl`, only if the wall you pick has LEDs."),
    ("**Un marco trasero:** `frame_pi4.stl` o `frame_pi5.stl`, según tu Raspberry Pi.",
     "**One back frame:** `frame_pi4.stl` or `frame_pi5.stl`, for your Raspberry Pi."),
    ("**HDMI trasero (opcional):** `hdmi_holder.stl` o `hdmi_cover.stl`, o ninguno (ver su apartado).",
     "**HDMI on the back (optional):** `hdmi_holder.stl` or `hdmi_cover.stl`, or neither (see its section)."),
    ("**Orejas y tapas ciegas:** 5 × `ear.stl` (4 y 1 de repuesto) y 4 × `ear_blank.stl`.",
     "**Ears and blanks:** 5 × `ear.stl` (4 and 1 spare) and 4 × `ear_blank.stl`."),
    ("**Tapas de conectores (opcional):** las de `blanks/` de los conectores que no uses.",
     "**Connector blanks (optional):** those in `blanks/` for the connectors you don't use."),
]

DECIDE_HEAD = (["¿Ver los LEDs de la placa de la Pico?", "¿Tienes AMS?", "Imprime"],
               ["See the Pico board's LEDs?", "Do you have an AMS?", "Print"])
DECIDE = ([["No", "Sí", "A · `wall_multicolor_bambu.3mf`"],
           ["No", "No", "B · `wall_monocolor.stl` (logo grabado, un color)"],
           ["Sí", "Sí", "C · `leds/wall_led_multicolor_bambu.3mf` + lentillas"],
           ["Sí", "No, pero quiero el logo en colores", "D · `no_ams/wall_led_no_ams.stl` + 3 rellenos + lentillas"],
           ["Sí", "No, un solo color me vale", "E · `leds/wall_led_monocolor.stl` + lentillas"]],
          [["No", "Yes", "A · `wall_multicolor_bambu.3mf`"],
           ["No", "No", "B · `wall_monocolor.stl` (engraved logo, one colour)"],
           ["Yes", "Yes", "C · `leds/wall_led_multicolor_bambu.3mf` + lenses"],
           ["Yes", "No, but I want the logo in colour", "D · `no_ams/wall_led_no_ams.stl` + 3 fillings + lenses"],
           ["Yes", "No, one colour is fine", "E · `leds/wall_led_monocolor.stl` + lenses"]])

# section: (title, intro, pieces); piece: (image, files, name, what it is, when, how to print)
SECTIONS = [
    (("1 · Pared principal (elige una)", "1 · Main wall (pick one)"),
     ("La pared grande con la ventana de la OLED, el pulsador DISPLAY y las bahías por donde se conectan los "
      "sensores desde fuera. Las cinco tienen los mismos insertos y encajan igual con la base y la tapa: solo "
      "cambian el logo y los LEDs.",
      "The large wall with the OLED window, the DISPLAY button and the bays where the sensors plug in from "
      "outside. All five have the same inserts and fit the base and the shell the same way: only the logo and "
      "the LEDs change."),
     [("wall_multicolor", ["wall_multicolor_bambu.3mf", "wall_multicolor.3mf"],
       ("A · Pared con logo en 4 colores", "A · Wall with the logo in 4 colours"),
       ("Pared sin agujeros de LEDs, logo marino, azul y gris incrustado a ras.",
        "Wall without LED holes, navy, blue and grey logo inlaid flush."),
       ("Tienes AMS (o cualquier multimaterial) y no te interesa ver los LEDs de la placa.",
        "You have an AMS (or any multi-material) and don't need to see the board's LEDs."),
       ("Cara del logo sobre la cama. AMS: 1 blanco, 2 marino, 3 azul, 4 gris. `_bambu.3mf` para Bambu Studio; "
        "el `.3mf` genérico para otros laminadores.",
        "Logo face on the bed. AMS: 1 white, 2 navy, 3 blue, 4 grey. `_bambu.3mf` for Bambu Studio; "
        "the generic `.3mf` for other slicers.")),
      ("wall_monocolor", ["wall_monocolor.stl"], ("B · Pared de un color", "B · Single-colour wall"),
       ("La misma pared, con el logo grabado 1 mm en vez de incrustado.",
        "The same wall, with the logo engraved 1 mm instead of inlaid."),
       ("No tienes AMS y no necesitas los LEDs. La más sencilla de imprimir.",
        "No AMS and no need for the LEDs. The easiest one to print."),
       ("Cara del logo sobre la cama, un solo filamento.", "Logo face on the bed, one filament.")),
      ("wall_led_multicolor", ["leds/wall_led_multicolor_bambu.3mf", "leds/wall_led_multicolor.3mf"],
       ("C · Pared con LEDs, logo en 4 colores", "C · LED wall, logo in 4 colours"),
       ("Un agujero sobre cada uno de los 10 LEDs de la placa de la Pico (VL1–VL4, US1–US5, PWR), con un tubo "
        "por dentro hasta el LED, y otro sobre el LED de la propia Pico. Cada boca lleva un chaflán de 0,4 mm.",
        "A hole over each of the Pico board's 10 LEDs (VL1–VL4, US1–US5, PWR), with a tube inside down to the "
        "LED, and one over the Pico's own LED. Each mouth has a 0.4 mm chamfer."),
       ("Quieres ver desde fuera qué sensores están activos y tienes AMS.",
        "You want to see from outside which sensors are active, and you have an AMS."),
       ("Cara del logo sobre la cama. AMS: 1 blanco, 2 marino, 3 azul, 4 gris. Necesita las lentillas.",
        "Logo face on the bed. AMS: 1 white, 2 navy, 3 blue, 4 grey. Needs the lenses.")),
      ("wall_led_no_ams", ["no_ams/wall_led_no_ams.stl"],
       ("D · Pared con LEDs sin AMS", "D · LED wall without AMS"),
       ("La pared C con el logo en hueco de 1,4 mm, para rellenarlo con piezas impresas aparte. "
        "Tubos, lentillas e insertos iguales que en C.",
        "Wall C with the logo as 1.4 mm pockets, filled with parts printed apart. "
        "Same tubes, lenses and inserts as C."),
       ("Quieres los LEDs y el logo en colores, pero tu impresora no tiene AMS.",
        "You want the LEDs and the logo in colour, but your printer has no AMS."),
       ("Blanco, cara del logo sobre la cama. Necesita los 3 rellenos y las lentillas.",
        "White, logo face on the bed. Needs the 3 fillings and the lenses.")),
      ("inlays", ["no_ams/inlay_navy.stl", "no_ams/inlay_blue.stl", "no_ams/inlay_grey.stl"],
       ("D · Rellenos del logo", "D · Fillings for the logo"),
       ("Marino: «ROS». Azul: «2D2» y los 12 puntos. Gris: el marco de los puntos, ensanchado hacia dentro "
        "a 1,7 mm (1,2 bajo la fila de abajo) para que se pueda imprimir y manejar. 1,4 mm de grueso (7 capas), "
        "0,1 mm de holgura por lado, a ras de la pared.",
        "Navy: \"ROS\". Blue: \"2D2\" and the 12 dots. Grey: the dots' frame, widened inwards to 1.7 mm "
        "(1.2 under the bottom row) so it prints and handles. 1.4 mm thick (7 layers), 0.1 mm of play per side, "
        "flush with the wall."),
       ("Solo con la pared D.", "Only with wall D."),
       ("Una placa por color, cara vista sobre la cama, capas de 0,2 mm, sin borde. Salen en su sitio y en "
        "espejo: dales la vuelta, mételos en su hueco y fíjalos con una gota de cianoacrilato.",
        "One plate per colour, visible face on the bed, 0.2 mm layers, no brim. They come out in place and "
        "mirrored: turn them over, press them into their pockets and fix them with a drop of cyanoacrylate.")),
      ("wall_led_monocolor", ["leds/wall_led_monocolor.stl"],
       ("E · Pared con LEDs de un color", "E · Single-colour LED wall"),
       ("La pared C con el logo grabado 1 mm.", "Wall C with the logo engraved 1 mm."),
       ("Quieres los LEDs, no tienes AMS y un solo color te vale.", "You want the LEDs, no AMS, one colour is fine."),
       ("Cara del logo sobre la cama, un solo filamento. Necesita las lentillas.",
        "Logo face on the bed, one filament. Needs the lenses.")),
      ("led_lenses", ["leds/led_lenses.stl"], ("Lentillas de los LEDs", "LED lenses"),
       ("13 discos (11 y 2 de repuesto) que se meten en la boca de cada agujero, a ras de la pared, con 0,25 mm "
        "de holgura; si alguno baila, una gota de pegamento.",
        "13 discs (11 and 2 spares) that drop into the mouth of each hole, flush with the wall, with 0.25 mm of "
        "play; if one is loose, a drop of glue."),
       ("Con cualquier pared con LEDs: C, D o E.", "With any LED wall: C, D or E."),
       ("PLA translúcido (o PETG transparente), discos planos sobre la cama.",
        "Translucent PLA (or clear PETG), discs flat on the bed.")),
      ]),
    (("2 · Piezas comunes (siempre)", "2 · Common parts (always)"),
     ("Las mismas con cualquier pared.", "The same with any wall."),
     [("base", ["base.stl"], ("Base", "Base"),
       ("Suelo, frontal estrecha (XT60, interruptor y rejilla), trasera, tabique central (Pi y convertidor) y los "
        "rebajes de las orejas.",
        "Floor, narrow front (XT60, switch and vent), back, central divider (Pi and converter) and the ear "
        "pockets."),
       ("Siempre.", "Always."), ("Suelo sobre la cama.", "Floor on the bed.")),
      ("shell", ["shell.stl"], ("Tapa", "Shell"),
       ("Techo y lateral en una pieza que baja desde arriba; la frontal se queda con la base.",
        "Roof and side in one piece that slides down from above; the front stays with the base."),
       ("Siempre.", "Always."), ("Techo sobre la cama.", "Roof on the bed.")),
      ("push_rod", ["push_rod.stl"], ("Varilla del pulsador DISPLAY", "DISPLAY push rod"),
       ("Atraviesa la pared y pulsa el botón DISPLAY de la placa de la Pico.",
        "Goes through the wall and presses the Pico board's DISPLAY button."),
       ("Siempre.", "Always."), ("De pie.", "Standing.")),
      ("ear", ["ear.stl"], ("Oreja de fijación", "Mounting ear"),
       ("Pieza en L que va a ras en un rebaje de la frontal o de la trasera con 2 M3 × 8 avellanados; su lengüeta "
        "(agujero de 4,3 mm) se atornilla al R2. Sirve para la caja de pie (4 orejas en los rebajes junto al suelo) "
        "o tumbada sobre el lateral de la tapa (4 en los rebajes junto a ese lateral).",
        "An L piece flush in a pocket of the front or the back with 2 M3 × 8 countersunk; its lug (4.3 mm hole) "
        "screws to the R2. Works with the box standing (4 ears in the pockets by the floor) or lying on the shell's "
        "side (4 in the pockets by that side)."),
       ("Siempre: 5 (4 y 1 de repuesto).", "Always: 5 (4 and 1 spare)."),
       ("De canto, con el perfil de la L sobre la cama: cada capa lleva la L entera y no se parte por el codo.",
        "On edge, the L's profile on the bed: every layer holds the whole L, so it does not split at the bend.")),
      ("ear_blank", ["ear_blank.stl"], ("Tapa ciega de oreja", "Ear blank"),
       ("La placa de la oreja sin lengüeta: cierra a ras los 4 rebajes que no usas, con sus 2 tornillos.",
        "The ear's plate without the lug: closes the 4 pockets you don't use flush, with its 2 screws."),
       ("Siempre: 4.", "Always: 4."), ("Plana, cara vista sobre la cama.", "Flat, visible face on the bed.")),
      ("blanks_all", ["blanks/blank_US1.stl … blank_EXP.stl", "blanks/blanks_all.stl"],
       ("Tapas de los conectores sin usar", "Blanks for the unused connectors"),
       ("Solo estética: una por conector de sensor (US1–US5, VL1–VL4, EXP). Se clava en los pines del conector "
        "como un Dupont y cierra a ras su franja de la abertura; los conectores con sensor quedan abiertos. Para "
        "quitarla, mete la uña en el chaflán de un borde. Si se cae o entra muy dura, ajusta `blank_pin_d` "
        "(1,0 mm) en `params.scad`.",
        "Looks only: one per sensor connector (US1–US5, VL1–VL4, EXP). It plugs onto the connector's pins like a "
        "Dupont and closes its strip of the opening flush; the connectors with a sensor stay open. To take it "
        "out, put a nail in the chamfer on one edge. If it falls out or goes in too hard, change `blank_pin_d` "
        "(1.0 mm) in `params.scad`."),
       ("Opcional: las de los conectores que no uses (o `blanks_all.stl`, las diez).",
        "Optional: those of the connectors you don't use (or `blanks_all.stl`, all ten)."),
       ("Cara vista sobre la cama, del color de la pared.", "Visible face on the bed, in the wall's colour.")),
      ]),
    (("3 · Marco trasero (elige uno)", "3 · Back frame (pick one)"),
     ("Cierra la ventana de la trasera alrededor de los USB y el Ethernet de la Pi. La Pi 4 y la Pi 5 tienen "
      "esos conectores al revés, por eso hay dos.",
      "Closes the back window round the Pi's USB and Ethernet jacks. The Pi 4 and the Pi 5 have them the "
      "other way round, hence two frames."),
     [("frame_pi4", ["frame_pi4.stl"], ("Marco para la Pi 4", "Frame for the Pi 4"),
       ("Ethernet arriba, USB abajo.", "Ethernet at the top, USB below."),
       ("Si montas una Raspberry Pi 4.", "If you fit a Raspberry Pi 4."),
       ("Cara exterior sobre la cama.", "Outer face on the bed.")),
      ("frame_pi5", ["frame_pi5.stl"], ("Marco para la Pi 5", "Frame for the Pi 5"),
       ("Ethernet abajo, USB arriba.", "Ethernet at the bottom, USB above."),
       ("Si montas una Raspberry Pi 5.", "If you fit a Raspberry Pi 5."),
       ("Cara exterior sobre la cama.", "Outer face on the bed.")),
      ]),
    (("4 · HDMI trasero (opcional)", "4 · HDMI on the back (optional)"),
     ("La base ya trae la ventana del HDMI y dos insertos M3. Según lo que pongas ahí:",
      "The base already has the HDMI window and two M3 inserts. Depending on what goes there:"),
     [("hdmi_holder", ["hdmi_holder.stl"], ("Soporte HDMI para kit FPC", "HDMI holder for an FPC kit"),
       ("Capucha que sujeta la placa «A hembra» de un kit HDMI FPC (de FPV): clavija micro-HDMI a 90°, cinta "
        "plana y placa HDMI A hembra. La cinta entra por la ventana y va bajo la Pi hasta su HDMI 0.",
        "A hood holding the \"A Female\" board of an FPV FPC HDMI kit: 90° micro-HDMI plug, flat ribbon and "
        "HDMI A female board. The ribbon goes in through the window and under the Pi to its HDMI 0."),
       ("Usas el kit HDMI FPC. Mide la placa A hembra antes de imprimir (`fpc_a` en `hdmi_fpc.scad`).",
        "You use the FPC HDMI kit. Measure the A Female board before printing (`fpc_a` in `hdmi_fpc.scad`)."),
       ("Cara exterior sobre la cama, capucha hacia arriba. 2 × M3 × 8 avellanados.",
        "Outer face on the bed, hood up. 2 × M3 × 8 countersunk.")),
      ("hdmi_cover", ["hdmi_cover.stl"], ("Tapa HDMI ciega", "Blank HDMI cover"),
       ("Tapa la ventana del HDMI con un tapón que la rellena.", "Closes the HDMI window with a plug that fills it."),
       ("No pones HDMI.", "No HDMI fitted."),
       ("Cara exterior sobre la cama. 2 × M3 × 8 avellanados.", "Outer face on the bed. 2 × M3 × 8 countersunk.")),
      ]),
]
HDMI_NOTE = ("Si usas un **HDMI hembra de panel con brida y 2 tornillos M3**, no hace falta imprimir nada: se "
             "atornilla directamente a los insertos de la base.",
             "With a **panel HDMI female jack with a flange and 2 M3 screws** nothing needs printing: it screws "
             "straight onto the base's inserts.")

NOT_TO_PRINT = [
    ("`wall.stl`, `logo_navy.stl`, `logo_blue.stl`, `logo_grey.stl`",
     ("Son las 4 partes que van dentro de `wall_multicolor*.3mf`. Úsalas solo para montar tu propio proyecto "
      "multicolor en un laminador que no lea el 3MF.",
      "The 4 bodies inside `wall_multicolor*.3mf`. Use them only to build your own multicolour project in a "
      "slicer that can't read the 3MF.")),
    ("`leds/wall_led.stl`, `leds/logo_*_led.stl`",
     ("Lo mismo para `wall_led_multicolor*.3mf`.", "The same for `wall_led_multicolor*.3mf`.")),
]


# --- output ---------------------------------------------------------------------------------------------
def render_images():
    IMG.mkdir(exist_ok=True)
    for name, cam in VIEWS.items():
        r = subprocess.run([OPENSCAD, "-o", str(IMG / f"{name}.png"), "-D", f'pieza="{name}"', "--imgsize=1200,900",
                            f"--camera=0,0,0,{cam},0", "--viewall", "--autocenter", "--colorscheme=Tomorrow",
                            str(HERE / "parts.scad")], capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        if r.returncode or "ERROR" in out or "WARNING" in out:
            raise RuntimeError(f"{name}: {out[-1500:]}")
        print("ok", name, flush=True)


def lang_texts(lang):
    i = 0 if lang == "es" else 1
    return i, {k: v[i] for k, v in T.items()}


def files_md(files):
    return " · ".join(f"`stl/{f}`" for f in files)


def write_md(lang, path):
    i, t = lang_texts(lang)
    L = ['<img src="../../../media/ros2d2-logo.png" alt="ROS2D2" width="360"> '
         '<img src="../../../media/astromech-spain-logo-circular.png" alt="Astromech Spain" width="70">', "",
         f"# {t['title']}", "", t["other"], "", t["intro"], "", f"**{t['latest']}:** <{REPO_URL}>", "",
         f"## {t['what']}", ""]
    L += [f"- {c[i]}" for c in CHECKLIST]
    L += ["", f"### {t['which']}", "", "| " + " | ".join(DECIDE_HEAD[i]) + " |", "|---|---|---|"]
    L += ["| " + " | ".join(r) + " |" for r in DECIDE[i]]
    L += ["", t["general"]]
    for k, (title, intro, pieces) in enumerate(SECTIONS):
        L += ["", f"## {title[i]}", "", intro[i]]
        for img, files, name, what, when, how in pieces:
            L += ["", f"### {name[i]}", "", f'<img src="img/{img}.png" alt="{name[i]}" width="480">', "",
                  f"**{t['files']}:** {files_md(files)}", "", f"**{t['is']}:** {what[i]}", "",
                  f"**{t['when']}:** {when[i]}", "", f"**{t['how']}:** {how[i]}"]
        if k == len(SECTIONS) - 1:
            L += ["", HDMI_NOTE[i]]
    L += ["", f"## {t['skip']}", "", "| " + " | ".join(t["skip_head"]) + " |", "|---|---|"]
    L += [f"| {f} | {w[i]} |" for f, w in NOT_TO_PRINT]
    path.write_text("\n".join(L) + "\n", encoding="utf8")
    print("ok", path.name, flush=True)


def md_inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def write_html(lang, path):
    i, t = lang_texts(lang)
    e = md_inline
    rows = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in DECIDE[i])
    body = ""
    for k, (title, intro, pieces) in enumerate(SECTIONS):
        body += f"<h2 class=sec>{e(title[i])}</h2><p>{e(intro[i])}</p>"
        for img, files, name, what, when, how in pieces:
            body += (f"<section class=card><img src='{(IMG / f'{img}.png').as_uri()}'><div><h3>{e(name[i])}</h3>"
                     f"<p class=files>{e(files_md(files))}</p><p><b>{t['is']}:</b> {e(what[i])}</p>"
                     f"<p><b>{t['when']}:</b> {e(when[i])}</p><p><b>{t['how']}:</b> {e(how[i])}</p></div></section>")
        if k == len(SECTIONS) - 1:
            body += f"<p class=note>{e(HDMI_NOTE[i])}</p>"
    skip = "".join(f"<tr><td>{e(f)}</td><td>{e(w[i])}</td></tr>" for f, w in NOT_TO_PRINT)
    heads = "".join(f"<th>{html.escape(h)}</th>" for h in DECIDE_HEAD[i])
    checklist = "".join(f"<li>{e(c[i])}</li>" for c in CHECKLIST)
    skip_head = "".join(f"<th>{h}</th>" for h in t["skip_head"])
    doc = f"""<!doctype html><html lang={lang}><meta charset=utf-8><title>{html.escape(t['title'])}</title>
<style>
@page {{ size: A4; margin: 12mm 12mm 16mm;
  @bottom-left {{ content: "ROS2D2 · {t['latest']}: {REPO_URL}"; font: 8pt Segoe UI, Arial, sans-serif; color: #555; }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font: 8pt Segoe UI, Arial, sans-serif; color: #555; }} }}
body {{ font-family: Segoe UI, Arial, sans-serif; color: #1d1d1f; font-size: 10pt; }}
h1 {{ font-size: 19pt; margin: 0 0 3mm; }} h2 {{ font-size: 13pt; margin: 5mm 0 2mm; }} h3 {{ font-size: 11.5pt; margin: 0 0 1.5mm; }}
.logos {{ display: flex; align-items: center; justify-content: space-between; margin: 0 0 4mm; }}
.logos .r {{ height: 15mm; }} .logos .a {{ height: 24mm; }}
.latest {{ border: 1.5px solid #2a6fdb; border-radius: 2mm; padding: 2mm 3mm; margin: 3mm 0; }} .latest a {{ color: #2a6fdb; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 3mm; }}
td, th {{ border-bottom: 1px solid #ddd; padding: 1.2mm 2mm; text-align: left; vertical-align: top; }}
th {{ background: #f0f2f5; }}
.sec {{ page-break-before: always; }}
.card {{ display: flex; gap: 4mm; border: 1.2px solid #bbb; border-radius: 2.5mm; padding: 3mm; margin: 0 0 4mm;
        page-break-inside: avoid; }}
.card img {{ width: 70mm; height: 52mm; object-fit: contain; flex: none; }}
.card p {{ margin: 0 0 1.4mm; }} .files {{ color: #2a4f9b; }} code {{ font-size: 8.8pt; }}
.note {{ border-left: 3px solid #2a6fdb; padding: 1mm 3mm; }}
</style>
<div class=logos><img class=r src='{LOGO_ROS2D2.as_uri()}' alt="ROS2D2"><img class=a src='{LOGO_ASTROMECH.as_uri()}' alt="Astromech Spain"></div>
<h1>{html.escape(t['title'])}</h1><p>{e(t['intro'])}</p>
<div class=latest><b>{t['latest']}:</b> <a href='{REPO_URL}'>{REPO_URL}</a></div>
<h2>{t['what']}</h2><ul>{checklist}</ul>
<h3>{t['which']}</h3><table><tr>{heads}</tr>{rows}</table>
<p>{e(t['general'])}</p>
{body}
<h2>{t['skip']}</h2><table><tr>{skip_head}</tr>{skip}</table>
</html>"""
    path.write_text(doc, encoding="utf8")


def print_pdf(html_path, pdf_path):
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not browser:
        print("no Edge/Chrome: skipping", pdf_path.name)
        return
    # its own throw-away profile: with the browser already open, a headless run on the user's profile prints nothing
    before = pdf_path.stat().st_mtime if pdf_path.exists() else 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as prof:   # the browser may still hold a file in it
        r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={prof}",
                            f"--print-to-pdf={pdf_path}", html_path.as_uri()], capture_output=True, text=True, timeout=300)
        for _ in range(20):                                                       # it can finish writing just after it returns
            if pdf_path.exists() and pdf_path.stat().st_mtime > before:
                break
            time.sleep(0.5)
    if not pdf_path.exists() or pdf_path.stat().st_mtime <= before:
        raise RuntimeError(f"{pdf_path.name} not written: {(r.stdout + r.stderr)[-800:]}")
    print("ok", pdf_path.name, flush=True)


def main(images=True):
    if images:
        render_images()
    for lang, name in NAMES.items():
        write_md(lang, HERE / f"{name}.md")
        with tempfile.TemporaryDirectory() as tmp:
            h = pathlib.Path(tmp) / "guia.html"
            write_html(lang, h)
            print_pdf(h, HERE / f"{name}.pdf")


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv[1:])
