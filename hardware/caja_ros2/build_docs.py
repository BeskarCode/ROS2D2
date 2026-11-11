# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The assembly guide, IKEA style, in Spanish and English, with its hardware BOM.

    python -I hardware/caja_ros2/build_docs.py            # images + MONTAJE.md + ASSEMBLY.md + PDFs
    python -I hardware/caja_ros2/build_docs.py --no-images

Everything comes from the model: the images from montaje.scad, the BOM and each step's hardware
from the table in fasteners.scad (so they always match the holes).
"""
import ast
import collections
import html
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
IMG = HERE / "montaje" / "img"
REPO = HERE.parents[1]
LOGO_ROS2D2 = REPO / "media" / "ros2d2-logo.png"
LOGO_ASTROMECH = REPO / "hardware" / "r2_pico_carrier" / "gen" / "astromech-spain-logo-circular.png"   # dark on white
REPO_URL = "https://github.com/BeskarCode/ROS2D2"
BOX_DIMS = (107, 133, 125)          # W x D x H, mm (the rack box sets its own)


def repo_link():
    """Where the up-to-date guide, STL and sources of this box live (the PDF may be old)."""
    return f"{REPO_URL}/tree/main/hardware/{HERE.name}"

# scene -> (extra -D, camera rotation x, z)
VIEWS = {
    "montada": ('scene="montada"', 62, 35),
    "montada_atras": ('scene="montada_atras"', 58, 205),
    "interior": ('scene="abierta"', 55, 320),
    "despiece": ('scene="despiece"', 60, 300),
    "paso1": ('scene="paso";step=1', 50, 330),
    "paso2": ('scene="paso";step=2', 55, 330),
    "paso3": ('scene="paso";step=3', 60, 200),
    "paso4": ('scene="paso";step=4', 55, 290),
    "paso5": ('scene="paso";step=5', 55, 140),
    "paso6": ('scene="paso";step=6', 65, 300),
    "paso7": ('scene="paso";step=7', 55, 330),
    "paso8": ('scene="paso";step=8', 55, 200),
}

NAMES = {
    "ins_m3": ("Inserto térmico M3 (5,7 mm de largo, agujero de 4,0 mm)", "M3 heat-set insert (5.7 mm long, 4.0 mm hole)"),
    "m3x8_flat": ("Tornillo M3 × 8 de cabeza avellanada (ISO 10642)", "M3 × 8 countersunk screw (ISO 10642)"),
    "m3x6_pan": ("Tornillo M3 × 6 de cabeza alomada (ISO 7380)", "M3 × 6 button head screw (ISO 7380)"),
    "m3x6_cyl": ("Tornillo M3 × 6 de cabeza cilíndrica (DIN 912)", "M3 × 6 socket head cap screw (DIN 912)"),
    "m3x10_flat": ("Tornillo M3 × 10 de cabeza avellanada (ISO 10642)", "M3 × 10 countersunk screw (ISO 10642)"),
    "nut_m3": ("Tuerca M3 (DIN 934)", "M3 nut (DIN 934)"),
    "m25x6": ("Tornillo M2.5 × 6 (más largo si el ventilador de la Pi lleva separadores)",
              "M2.5 × 6 screw (longer if the Pi's fan sits on spacers)"),
    "m4x12": ("Tornillo M4 × 12 (o el que pida el soporte del R2)", "M4 × 12 screw (or what the R2's mount needs)"),
}
SHORT = {"ins_m3": "inserto M3", "m3x8_flat": "M3 × 8 avellanado", "m3x6_pan": "M3 × 6", "m3x6_cyl": "M3 × 6 cilíndrico",
         "m3x10_flat": "M3 × 10 avellanado", "nut_m3": "tuerca M3", "m25x6": "M2.5 × 6", "m4x12": "M4 × 12"}
SHORT_EN = {"ins_m3": "M3 insert", "m3x8_flat": "M3 × 8 countersunk", "m3x6_pan": "M3 × 6", "m3x6_cyl": "M3 × 6 socket head",
            "m3x10_flat": "M3 × 10 countersunk", "nut_m3": "M3 nut", "m25x6": "M2.5 × 6", "m4x12": "M4 × 12"}

OTHER = [
    ("1", "Interruptor de balancín KCD1 (agujero de panel 19,2 × 13 mm)", "KCD1 rocker switch (panel hole 19.2 × 13 mm)"),
    ("1", "Conector XT60E-F de panel (AMASS)", "XT60E-F panel connector (AMASS)"),
    ("1", "Cable micro-USB 2.0 a USB-A, codo lateral 90°, 30 cm (ver «Conectores acodados»)",
     "micro-USB 2.0 to USB-A cable, 90° side angle, 30 cm (see «Angled plugs»)"),
    ("1", "Cable USB-C macho con hilos (5 V a la Pi), 3 A, 15–20 cm; recto o acodado 90°",
     "USB-C male pigtail (5 V to the Pi), 3 A, 15–20 cm; straight or 90° angled"),
    ("—", "Cable de 0,5 mm² para los 5 V del borne J1 y de 1 mm² para los 24 V", "0.5 mm² wire for the 5 V to terminal J1, 1 mm² for the 24 V"),
    ("1", "Pasacables en tira para la ranura de 35 × 10 mm", "Edge grommet strip for the 35 × 10 mm slot"),
]
PRINTED = [
    ("frontal_multicolor_bambu.3mf", "Frontal con el logo en 4 colores (AMS: blanco, marino, azul, gris)", "Front with the logo in 4 colours (AMS: white, navy, blue, grey)"),
    ("frontal_monocolor.stl", "o bien: frontal de un color, logo grabado", "or: single-colour front, engraved logo"),
    ("base.stl", "Base: suelo, trasera, soporte de la Pi", "Base: floor, back, Pi bracket"),
    ("carcasa.stl", "Carcasa en U (techo + laterales)", "U shell (roof + sides)"),
    ("pulsador.stl", "Varilla del pulsador DISPLAY", "DISPLAY push rod"),
]

STEPS = [
    {"n": 1,
     "es": {"title": "Insertos térmicos",
            "text": "Con el soldador a unos 220 °C, mete los insertos rectos y a ras: en el frontal, 4 en las "
                    "columnas, 2 en las pestañas de abajo y 1 en la de arriba; en la base, 4 en los bloques del "
                    "suelo, 2 en los tetones del convertidor y 1 en la pestaña de arriba."},
     "en": {"title": "Heat-set inserts",
            "text": "With the soldering iron at about 220 °C, press the inserts in straight and flush: on the "
                    "front, 4 in the columns, 2 in the bottom tabs and 1 in the top tab; on the base, 4 in the "
                    "floor blocks, 2 in the converter bosses and 1 in the top tab."}},
    {"n": 2,
     "es": {"title": "Convertidor 24 → 5 V",
            "text": "Atorníllalo a sus dos tetones, con los cables hacia la trasera. Comprueba con el calibre la "
                    "posición de sus agujeros (`conv_holes`) antes de imprimir la base."},
     "en": {"title": "24 → 5 V converter",
            "text": "Screw it onto its two bosses, wires towards the back. Check its holes (`conv_holes`) with a "
                    "caliper before printing the base."}},
    {"n": 3,
     "es": {"title": "XT60 e interruptor",
            "text": "Desde fuera: el XT60E-F con 2 tornillos y sus tuercas por dentro, y el interruptor a presión. "
                    "Cablea los 24 V: XT60 → interruptor → entrada del convertidor."},
     "en": {"title": "XT60 and switch",
            "text": "From the outside: the XT60E-F with 2 screws and their nuts inside, and the switch snapped "
                    "in. Wire the 24 V: XT60 → switch → converter input."}},
    {"n": 4,
     "es": {"title": "Raspberry Pi",
            "text": "Ponla junto al soporte unos milímetros adelantada y deslízala hacia atrás hasta que los USB y "
                    "el Ethernet asomen a ras por la trasera. Atorníllala y conecta el USB-C de 5 V del convertidor."},
     "en": {"title": "Raspberry Pi",
            "text": "Hold it against the bracket a few mm forward and slide it back until the USB and Ethernet "
                    "jacks come flush out of the back. Screw it on and plug in the 5 V USB-C from the converter."}},
    {"n": 5,
     "es": {"title": "Varilla y placa de la Pico",
            "text": "Mete la varilla del pulsador desde dentro por su guía. Atornilla la placa a las 4 columnas, "
                    "con los componentes hacia el frontal. Con el frontal aún suelto: aprieta los 5 V en el borne "
                    "J1, pincha el micro-USB acodado en la Pico y conecta los sensores."},
     "en": {"title": "Push rod and Pico board",
            "text": "Slide the push rod into its guide from the inside. Screw the board onto the 4 columns, "
                    "parts facing the front. With the front still loose: tighten the 5 V in terminal J1, plug "
                    "the angled micro-USB into the Pico and connect the sensors."}},
    {"n": 6,
     "es": {"title": "Frontal a la base",
            "text": "Pasa los cables de sensores y el micro-USB por los canales de los lados de la placa hasta la "
                    "ranura de la trasera. Atornilla el frontal desde debajo del suelo."},
     "en": {"title": "Front onto the base",
            "text": "Run the sensor cables and the micro-USB along the channels beside the board to the slot in "
                    "the back. Screw the front on from under the floor."}},
    {"n": 7,
     "es": {"title": "Carcasa",
            "text": "Bájala desde arriba y pon los 4 tornillos de los laterales y los 2 del techo."},
     "en": {"title": "Shell",
            "text": "Lower it from above and fit the 4 side screws and the 2 roof screws."}},
    {"n": 8,
     "es": {"title": "USB y fijación al R2",
            "text": "Saca el micro-USB por la ranura y enchúfalo en un USB de la Pi. Atornilla la caja al R2 por "
                    "sus 4 orejetas (con llave Allen: quedan a 6 mm de la pared)."},
     "en": {"title": "USB and onto the R2",
            "text": "Bring the micro-USB out through the slot into a Pi USB port. Screw the box to the R2 through "
                    "its 4 ears (use a hex key: they are 6 mm from the wall)."}},
]

TXT = {
    "es": {"title": "Caja ROS2 · Instrucciones de montaje", "built": "Montada", "back": "Por detrás",
           "inside": "Por dentro (sin carcasa)", "exploded": "Despiece", "bom": "Tornillería y material",
           "printed": "Piezas impresas", "other": "Otro material", "qty": "Cant.", "item": "Pieza", "where": "Paso",
           "step": "Paso", "you_need": "Necesitas", "nothing": "nada más", "wiring": "Conexiones", "angled": "Conectores acodados: hacia dónde sale el cable",
           "intro": "Caja mini torre para la Raspberry Pi 4, la placa de la Pico, el convertidor 24 → 5 V, el "
                    "XT60 y el interruptor. Antes de imprimir mide lo que indica el README (XT60, interruptor, "
                    "agujeros del convertidor, altura del pulsador y del ventilador).",
           "other_lang": "[English version](ASSEMBLY.md)",
           "latest": "Información actualizada, STL y fuentes", "size": "Tamaño frente al R2",
           "r2": "R2 ≈ 1,09 m", "boxlbl": "Caja", "scale": "R2 esquemático y caja a la misma escala"},
    "en": {"title": "ROS2 box · Assembly instructions", "built": "Assembled", "back": "From the back",
           "inside": "Inside (no shell)", "exploded": "Exploded view", "bom": "Hardware and parts",
           "printed": "Printed parts", "other": "Other parts", "qty": "Qty", "item": "Part", "where": "Step",
           "step": "Step", "you_need": "You need", "nothing": "nothing else", "wiring": "Wiring", "angled": "Angled plugs: which way the cable goes",
           "intro": "Mini-tower box for the Raspberry Pi 4, the Pico board, the 24 → 5 V converter, the XT60 and "
                    "the switch. Before printing, measure what the README lists (XT60, switch, converter holes, "
                    "button and fan heights).",
           "other_lang": "[Versión en castellano](MONTAJE.md)",
           "latest": "Up-to-date guide, STL and sources", "size": "Size next to the R2",
           "r2": "R2 ≈ 1.09 m", "boxlbl": "Box", "scale": "Schematic R2 and the box at the same scale"},
}


WIRING = {
    "es": {"battery": "Batería 24 V", "switch": "Interruptor", "conv": "Convertidor", "conv2": "24 → 5 V",
           "pi": "Raspberry Pi 4", "pico": "Placa de la Pico", "box": "Dentro de la caja",
           "usbc": "USB-C (5 V)", "usba": "USB-A", "micro": "micro-USB acodado: sale por la ranura y entra en un USB de la Pi",
           "mega": "Arduino Mega (Shadow)", "lidar": "Lidar C1",
           "us": "5× HC-SR04 → US1–US5", "us_p": "5V · TR · EC · G",
           "vl": "4× VL53L0X → VL1–VL4", "vl_p": "3V3 · G · SCL · SDA · – · XS  (cable ≤ 1 m)",
           "slot": "ranura trasera", "back": "trasera",
           "legend": [("#d62828", "+24 V"), ("#222222", "GND"), ("#e0b000", "+5 V"), ("#2a6fdb", "USB (datos)"), ("#8a8a8a", "cables de sensores")]},
    "en": {"battery": "24 V battery", "switch": "Switch", "conv": "Converter", "conv2": "24 → 5 V",
           "pi": "Raspberry Pi 4", "pico": "Pico board", "box": "Inside the box",
           "usbc": "USB-C (5 V)", "usba": "USB-A", "micro": "angled micro-USB: out through the slot into a Pi USB port",
           "mega": "Arduino Mega (Shadow)", "lidar": "Lidar C1",
           "us": "5× HC-SR04 → US1–US5", "us_p": "5V · TR · EC · G",
           "vl": "4× VL53L0X → VL1–VL4", "vl_p": "3V3 · G · SCL · SDA · – · XS  (cable ≤ 1 m)",
           "slot": "back slot", "back": "back",
           "legend": [("#d62828", "+24 V"), ("#222222", "GND"), ("#e0b000", "+5 V"), ("#2a6fdb", "USB (data)"), ("#8a8a8a", "sensor cables")]},
}


def scale_svg(lang):
    """A schematic astromech (front view, outline only) and the box, both in mm, same scale."""
    t = TXT[lang]
    W, D, H = BOX_DIMS
    G = 1160                                   # ground line, SVG y
    y = lambda z: G - z
    cx, R = 450, 228.5                         # body centre, body/dome radius (18 in)
    body = (330, 860)
    st = 'fill="#eef1f6" stroke="#1d1d1f" stroke-width="5" stroke-linejoin="round"'
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -40 1300 1220" width="1000" height="938" '
         f'font-family="Segoe UI, Arial, sans-serif" font-size="40">']
    s.append(f'<line x1="20" y1="{G}" x2="1280" y2="{G}" stroke="#888" stroke-width="4"/>')
    for sx in (-1, 1):                         # outer legs + feet, behind the body
        lx = cx + sx * (R + 25)
        s.append(f'<rect x="{lx - 45}" y="{y(900)}" width="90" height="{900 - 120}" rx="12" {st}/>')
        s.append(f'<path d="M{lx - 80},{y(0)} L{lx + 80},{y(0)} L{lx + 52},{y(140)} L{lx - 52},{y(140)} Z" {st}/>')
    s.append(f'<rect x="{cx - 55}" y="{y(body[0])}" width="110" height="{body[0] - 70}" {st}/>')          # centre leg
    s.append(f'<path d="M{cx - 95},{y(0)} L{cx + 95},{y(0)} L{cx + 65},{y(80)} L{cx - 65},{y(80)} Z" {st}/>')
    s.append(f'<rect x="{cx - R}" y="{y(body[1])}" width="{2 * R}" height="{body[1] - body[0]}" {st}/>')   # body
    s.append(f'<path d="M{cx - R},{y(body[1])} A{R},{R * 0.95} 0 0 1 {cx + R},{y(body[1])} Z" {st}/>')   # dome
    for sx in (-1, 1):                         # shoulder hubs
        s.append(f'<circle cx="{cx + sx * (R + 25)}" cy="{y(800)}" r="48" {st}/>')
    # height of the R2
    s.append(f'<line x1="{cx - R - 150}" y1="{y(0)}" x2="{cx - R - 150}" y2="{y(1090)}" stroke="#1d1d1f" stroke-width="3"/>')
    for z in (0, 1090):
        s.append(f'<line x1="{cx - R - 170}" y1="{y(z)}" x2="{cx - R - 130}" y2="{y(z)}" stroke="#1d1d1f" stroke-width="3"/>')
    s.append(f'<text x="{cx - R - 165}" y="{y(545)}" transform="rotate(-90 {cx - R - 165} {y(545)})" '
             f'text-anchor="middle">{html.escape(t["r2"])}</text>')
    # the box, front view (W x H), on the ground
    bx = 900
    s.append(f'<rect x="{bx}" y="{y(H)}" width="{W}" height="{H}" fill="#2a6fdb" stroke="#1d1d1f" stroke-width="4"/>')
    s.append(f'<text x="{bx}" y="{y(H) - 70}" font-weight="700">{html.escape(t["boxlbl"])}</text>')
    s.append(f'<text x="{bx}" y="{y(H) - 22}">{W} × {D} × {H} mm</text>')
    s.append("</svg>")
    return "\n".join(s)


def wiring_svg(lang):
    """Wiring diagram: power (24 V → XT60 → switch → converter → 5 V to the Pi and J1), USB, sensors."""
    t = WIRING[lang]
    e = html.escape
    R, K, Y, B, G = "#d62828", "#222222", "#e0b000", "#2a6fdb", "#8a8a8a"

    def box(x, y, w, h, fill, label, sub="", tc="#fff", fs=17):
        s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#222" stroke-width="2"/>'
        s += f'<text x="{x + w / 2}" y="{y + h / 2 - (8 if sub else -6)}" fill="{tc}" font-size="{fs}" font-weight="700" text-anchor="middle">{e(label)}</text>'
        if sub:
            s += f'<text x="{x + w / 2}" y="{y + h / 2 + 16}" fill="{tc}" font-size="14" text-anchor="middle">{e(sub)}</text>'
        return s

    def wire(pts, c, w=4, dash=""):
        d = " ".join(f"{x},{y}" for x, y in pts)
        return f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" {dash}/>'

    def lab(x, y, s, size=13, anchor="start", c="#222", bold=False):
        return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{c}"{" font-weight=\"700\"" if bold else ""}>{e(s)}</text>'

    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 640" width="1000" height="640" '
         'font-family="Segoe UI, Arial, sans-serif">', '<rect width="1000" height="640" fill="#ffffff"/>',
         '<rect x="215" y="30" width="590" height="470" rx="14" fill="#f4f6f8" stroke="#9aa3ad" stroke-width="2" stroke-dasharray="10 7"/>',
         lab(230, 55, t["box"], 15, c="#5b6570", bold=True)]
    # power chain
    s.append(box(20, 80, 150, 70, "#3d3d3d", t["battery"]))
    s.append(box(240, 85, 80, 60, "#f2c400", "XT60", tc="#222"))
    s.append(box(360, 85, 110, 60, "#c0282d", t["switch"], "KCD1"))
    s.append(box(510, 70, 160, 90, "#b9bec4", t["conv"], t["conv2"], tc="#222"))
    s.append(wire([(170, 105), (240, 105)], R)); s.append(wire([(170, 128), (240, 128)], K))
    s.append(wire([(320, 105), (360, 105)], R))
    s.append(wire([(470, 105), (510, 105)], R)); s.append(lab(476, 98, "IN+", 11, c=R))
    s.append(wire([(320, 128), (340, 128), (340, 165), (490, 165), (490, 135), (510, 135)], K)); s.append(lab(476, 182, "IN−", 11))
    s.append(lab(245, 78, t["back"], 12, c="#5b6570"))
    # Pi
    s.append(box(830, 60, 150, 200, "#1f7a3c", t["pi"]))
    s.append(lab(905, 300, t["usba"] + " ×4", 13, "middle", c="#1f7a3c", bold=True))
    # 5 V
    s.append(wire([(670, 100), (760, 100), (760, 90), (830, 90)], Y))
    s.append(wire([(670, 128), (775, 128), (775, 110), (830, 110)], K))
    s.append(lab(700, 84, t["usbc"], 13, c="#8a6d00", bold=True))
    s.append(wire([(690, 100), (690, 300), (520, 300), (520, 330)], Y))
    s.append(wire([(705, 128), (705, 315), (545, 315), (545, 330)], K))
    s.append(lab(512, 296, "OUT+ / OUT− → J1", 12, c="#8a6d00"))
    # Pico board
    s.append(box(420, 330, 330, 150, "#1f7a3c", t["pico"], "Pico 2 · OLED · DISPLAY"))
    s.append(lab(510, 350, "J1 +5V / GND", 12, c="#fff"))
    # USB data: Pico micro-USB out through the slot into a Pi USB-A
    s.append(wire([(700, 330), (700, 290), (815, 290), (815, 520), (850, 520), (850, 262)], B, 4, 'stroke-dasharray="9 6"'))
    s.append(lab(420, 522, t["micro"], 12, c=B))
    s.append(wire([(895, 262), (895, 560)], B, 4)); s.append(box(800, 560, 190, 40, "#e9edf2", t["mega"], tc="#222", fs=15))
    s.append(wire([(950, 262), (950, 420)], B, 4)); s.append(box(900, 420, 95, 38, "#e9edf2", t["lidar"], tc="#222", fs=15))
    # sensors through the back slot
    s.append(box(8, 360, 192, 46, "#e9edf2", t["us"], tc="#222", fs=14))
    s.append(lab(104, 425, t["us_p"], 12, "middle"))
    s.append(box(8, 470, 192, 46, "#e9edf2", t["vl"], tc="#222", fs=14))
    s.append(lab(104, 535, t["vl_p"], 11, "middle"))
    s.append(wire([(200, 383), (300, 383), (300, 395), (420, 395)], G, 6))
    s.append(wire([(200, 493), (735, 493), (735, 480)], G, 6))
    s.append(lab(232, 375, "US1–US5", 12, c="#555", bold=True)); s.append(lab(232, 486, "VL1–VL4", 12, c="#555", bold=True))
    s.append(f'<rect x="206" y="372" width="18" height="135" fill="none" stroke="#5b6570" stroke-width="2"/>')
    s.append(lab(206, 522, t["slot"], 12, c="#5b6570"))
    # legend
    for i, (c, name) in enumerate(t["legend"]):
        x = 20 + i * 190
        s.append(f'<line x1="{x}" y1="625" x2="{x + 40}" y2="625" stroke="{c}" stroke-width="5"/>')
        s.append(lab(x + 48, 630, name, 13))
    s.append("</svg>")
    return "\n".join(s) + "\n"


def fastener_table():
    """[[kind, step, pos, dir], ...] from fasteners.scad."""
    with tempfile.TemporaryDirectory() as d:
        scad = pathlib.Path(d) / "t.scad"
        scad.write_text(f'include <{(HERE / "fasteners.scad").as_posix()}>\necho("T", fasteners());\ncube(1);\n')
        out = pathlib.Path(d) / "t.echo"
        subprocess.run([OPENSCAD, "-o", str(out), str(scad)], capture_output=True, text=True, check=True)
        m = re.search(r'ECHO: "T", (.+)', out.read_text(encoding="utf8"))
    return ast.literal_eval(m.group(1))


def bom(table):
    c = collections.Counter(f[0] for f in table)
    steps = collections.defaultdict(set)
    for f in table:
        steps[f[0]].add(f[1])
    return [{"kind": k, "qty": c[k], "steps": sorted(steps[k])} for k in NAMES if c[k]]


def step_hw(table, n, lang):
    c = collections.Counter(f[0] for f in table if f[1] == n)
    short = SHORT if lang == "es" else SHORT_EN
    return [f"{q}× {short[k]}" for k, q in c.items()]


def write_guide(lang, table, path):
    t = TXT[lang]
    i = 0 if lang == "es" else 1
    L = ['<img src="../../media/ros2d2-logo.png" alt="ROS2D2" width="420">', "",
         f"# {t['title']}", "", t["other_lang"], "", t["intro"], "",
         f"| {t['built']} | {t['back']} |", "|---|---|",
         "| ![](montaje/img/montada.png) | ![](montaje/img/montada_atras.png) |", "",
         f"**{t['latest']}:** <{repo_link()}>", "",
         f"## {t['size']}", "", f'<img src="montaje/img/escala_{lang}.svg" alt="{t["size"]}" width="420">', "",
         f"## {t['inside']}", "", "![](montaje/img/interior.png)", "",
         f"## {t['exploded']}", "", "![](montaje/img/despiece.png)", "",
         f"## {t['bom']}", "", f"### {t['printed']}", "", f"| {t['item']} | |", "|---|---|"]
    L += [f"| `stl/{f}` | {(es, en)[i]} |" for f, es, en in PRINTED]
    L += ["", f"| {t['qty']} | {t['item']} | {t['where']} |", "|---|---|---|"]
    L += [f"| {r['qty']}× | {NAMES[r['kind']][i]} | {', '.join(map(str, r['steps']))} |" for r in bom(table)]
    L += ["", f"### {t['other']}", "", f"| {t['qty']} | {t['item']} |", "|---|---|"]
    L += [f"| {q} | {(es, en)[i]} |" for q, es, en in OTHER]
    L += ["", f"## {t['wiring']}", "", f"![](montaje/img/conexiones_{lang}.svg)"]
    L += ["", f"## {t['angled']}", "", f"![](montaje/img/conectores_{lang}.svg)"]
    for s in STEPS:
        hw = step_hw(table, s["n"], lang)
        L += ["", f"## {s['n']} · {s[lang]['title']}", "", f"![](montaje/img/paso{s['n']}.png)", "",
              f"**{t['you_need']}:** {', '.join(hw) if hw else t['nothing']}", "", s[lang]["text"]]
    path.write_text("\n".join(L) + "\n", encoding="utf8")


def write_html(lang, table, path):
    """A4 print version, one step per half page, for the PDF."""
    t = TXT[lang]
    i = 0 if lang == "es" else 1
    img = lambda n: (IMG / f"{n}.png").as_uri()
    e = html.escape
    rows = "".join(f"<tr><td>{r['qty']}×</td><td>{e(NAMES[r['kind']][i])}</td><td>{', '.join(map(str, r['steps']))}</td></tr>"
                   for r in bom(table))
    printed = "".join(f"<tr><td><code>{e(f)}</code></td><td>{e((es, en)[i])}</td></tr>" for f, es, en in PRINTED)
    other = "".join(f"<tr><td>{q}</td><td>{e((es, en)[i])}</td></tr>" for q, es, en in OTHER)
    steps = ""
    for s in STEPS:
        hw = step_hw(table, s["n"], lang)
        chips = "".join(f"<span class=chip>{e(h)}</span>" for h in hw) or f"<span class=none>{t['nothing']}</span>"
        txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", e(s[lang]["text"]))
        steps += (f"<section class=step><div class=num>{s['n']}</div><h2>{e(s[lang]['title'])}</h2>"
                  f"<img src='{img('paso%d' % s['n'])}'><div class=hw>{chips}</div><p>{txt}</p></section>")
    doc = f"""<!doctype html><html lang={lang}><meta charset=utf-8><title>{e(t['title'])}</title>
<style>
@page {{ size: A4; margin: 12mm 12mm 16mm;
  @bottom-left {{ content: "ROS2D2 · {e(t['latest'])}: {repo_link()}"; font: 8pt Segoe UI, Arial, sans-serif; color: #555; }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font: 8pt Segoe UI, Arial, sans-serif; color: #555; }} }}
body {{ font-family: Segoe UI, Arial, sans-serif; color: #1d1d1f; font-size: 10.5pt; }}
h1 {{ font-size: 20pt; margin: 0 0 4mm; }} h2 {{ font-size: 13pt; margin: 0 0 2mm; }}
.cover img {{ width: 49%; }} .wide {{ width: 100%; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 5mm; }}
td, th {{ border-bottom: 1px solid #ddd; padding: 1.2mm 2mm; text-align: left; vertical-align: top; }}
.step {{ position: relative; page-break-inside: avoid; border: 1.5px solid #222; border-radius: 3mm;
        padding: 4mm 4mm 3mm 22mm; margin: 0 0 5mm; min-height: 110mm; }}
.step img {{ width: 100%; max-height: 95mm; object-fit: contain; }}
.num {{ position: absolute; left: 4mm; top: 3mm; font-size: 30pt; font-weight: 800; }}
.chip {{ display: inline-block; border: 1.5px solid #222; border-radius: 2mm; padding: .6mm 2mm; margin: 0 1.5mm 1.5mm 0;
        font-weight: 600; }}
.none {{ color: #888; }} code {{ font-size: 9pt; }} .pb {{ page-break-before: always; }}
.logos {{ display: flex; align-items: center; justify-content: space-between; margin: 0 0 5mm; }}
.logos .r {{ height: 16mm; }} .logos .a {{ height: 26mm; }}
.latest {{ border: 1.5px solid #2a6fdb; border-radius: 2mm; padding: 2mm 3mm; margin: 3mm 0 4mm; }}
.latest a {{ color: #2a6fdb; }}
.size {{ display: flex; align-items: center; gap: 6mm; page-break-inside: avoid; }} .size svg {{ width: 70mm; height: auto; }}
</style>

<div class=logos><img class=r src='{LOGO_ROS2D2.as_uri()}' alt="ROS2D2"><img class=a src='{LOGO_ASTROMECH.as_uri()}' alt="Astromech Spain"></div>
<h1>{e(t['title'])}</h1><p>{e(t['intro'])}</p>
<div class=latest><b>{e(t['latest'])}:</b> <a href='{repo_link()}'>{e(repo_link())}</a></div>
<div class=cover><img src='{img("montada")}'><img src='{img("montada_atras")}'></div>
<div class=size><div>{scale_svg(lang)}</div><div><h2>{e(t['size'])}</h2><p>{e(t['scale'])}.</p></div></div>
<h2 class=pb>{e(t['exploded'])}</h2><img class=wide src='{img("despiece")}'>
<h2>{e(t['bom'])}</h2><h3>{e(t['printed'])}</h3><table>{printed}</table>
<table><tr><th>{t['qty']}</th><th>{t['item']}</th><th>{t['where']}</th></tr>{rows}</table>
<h3>{e(t['other'])}</h3><table>{other}</table>
<h2>{e(t['inside'])}</h2><img class=wide src='{img("interior")}'>
<h2 class=pb>{e(t['wiring'])}</h2>{wiring_svg(lang).replace('width="1000" height="640"', 'width="100%"')}
<h2>{e(t['angled'])}</h2>{(IMG / f"conectores_{lang}.svg").read_text(encoding="utf8").replace('width="1000" height="900"', 'width="100%"')}
<div class=pb></div>{steps}</html>"""
    path.write_text(doc, encoding="utf8")


def render_images():
    IMG.mkdir(parents=True, exist_ok=True)
    for name, (defs, rx, rz) in VIEWS.items():
        args = [OPENSCAD, "-o", str(IMG / f"{name}.png")]
        for d in defs.split(";"):
            args += ["-D", d]
        args += ["--imgsize=1600,1200", f"--camera=0,0,0,{rx},0,{rz},0", "--viewall", "--autocenter",
                 "--colorscheme=Tomorrow", str(HERE / "montaje.scad")]
        for attempt in range(4):           # Windows sometimes holds the PNG a moment (viewer, antivirus)
            r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
            if "Can't open file" not in r.stdout + r.stderr:
                break
            time.sleep(3)
        if r.returncode or "ERROR" in r.stdout + r.stderr or "Can't open file" in r.stdout + r.stderr:
            raise RuntimeError(f"{name}: {(r.stdout + r.stderr)[-1500:]}")
        print("ok", name, flush=True)


def print_pdf(html_path, pdf_path):
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not browser:
        print("no Edge/Chrome: skipping", pdf_path.name)
        return
    subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()], capture_output=True, timeout=300)
    print("ok", pdf_path.name, flush=True)


def main(images=True):
    if images:
        render_images()
    table = fastener_table()
    IMG.mkdir(parents=True, exist_ok=True)
    for lang in ("es", "en"):
        (IMG / f"conexiones_{lang}.svg").write_text(wiring_svg(lang), encoding="utf8")
        (IMG / f"escala_{lang}.svg").write_text(scale_svg(lang), encoding="utf8")
    write_guide("es", table, HERE / "MONTAJE.md")
    write_guide("en", table, HERE / "ASSEMBLY.md")
    for lang, name in (("es", "MONTAJE"), ("en", "ASSEMBLY")):
        h = HERE / "montaje" / f"{name}.html"
        write_html(lang, table, h)
        print_pdf(h, HERE / "montaje" / f"{name}.pdf")
        h.unlink()


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv)
