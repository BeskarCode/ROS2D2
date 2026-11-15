# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Print guide of the rack box: which files to print and when, one picture per piece (Spanish).

    python -I hardware/caja_ros2_rack/guia_impresion/build_guia.py [--no-images]

Renders each piece from its STL (run build.py first), writes GUIA_IMPRESION.md and GUIA_IMPRESION.pdf
(A4, through Edge or Chrome headless).
"""
import html
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
IMG = HERE / "img"
REPO = HERE.parents[2]
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
LOGO_ROS2D2 = REPO / "media" / "ros2d2-logo.png"
LOGO_ASTROMECH = REPO / "ros2_ws" / "src" / "r2_web" / "www" / "astromech-spain-logo.png"
REPO_URL = "https://github.com/BeskarCode/ROS2D2/tree/main/hardware/caja_ros2_rack"

WALL = "75,0,290"        # the walls stand as mounted, seen from outside
PART = "55,0,25"         # the rest in print orientation

# image -> camera
VIEWS = {"pared_multicolor": WALL, "pared_monocolor": WALL, "pared_led_multicolor": WALL,
         "pared_led_monocolor": WALL, "pared_led_sin_ams": WALL, "rellenos": WALL,
         "lentes_led": "35,0,25", "base": PART, "tapa": "235,0,25", "pulsador": PART,
         "marco_pi4": PART, "marco_pi5": PART, "soporte_hdmi": PART, "tapa_hdmi": PART}

# --- the guide ----------------------------------------------------------------------------------------
TITLE = "Caja ROS2 rack · Guía de impresión"
INTRO = ("Qué ficheros imprimir y cuándo elegir uno u otro. Solo para la caja rack "
         "(`hardware/caja_ros2_rack`). Todos los ficheros están en su carpeta `stl/`.")

CHECKLIST = [
    "**Siempre:** `base.stl`, `tapa.stl` y `pulsador.stl`.",
    "**Una pared principal** de las cinco opciones (tabla de abajo).",
    "**Lentillas** `con_leds/lentes_led.stl`, solo si la pared que eliges es con LEDs.",
    "**Un marco trasero:** `marco_pi4.stl` o `marco_pi5.stl`, según tu Raspberry Pi.",
    "**HDMI trasero (opcional):** `soporte_hdmi.stl` o `tapa_hdmi.stl`, o ninguno (ver su apartado).",
]

DECIDE_HEAD = ["¿Ver los LEDs de la placa de la Pico?", "¿Tienes AMS?", "Imprime"]
DECIDE = [
    ["No", "Sí", "A · `pared_multicolor_bambu.3mf`"],
    ["No", "No", "B · `pared_monocolor.stl` (logo grabado, un color)"],
    ["Sí", "Sí", "C · `con_leds/pared_led_multicolor_bambu.3mf` + lentillas"],
    ["Sí", "No, pero quiero el logo en colores", "D · `sin_ams/pared_led_sin_ams.stl` + 3 rellenos + lentillas"],
    ["Sí", "No, un solo color me vale", "E · `con_leds/pared_led_monocolor.stl` + lentillas"],
]

GENERAL = ("PETG, capa de 0,2 mm, boquilla de 0,4, sin soportes, salvo donde se indica otra cosa. "
           "Los insertos térmicos y los tornillos son los mismos con cualquier pared: mira la guía de montaje.")

# section title, intro, pieces: (image, files, name, what for, when, how to print)
SECTIONS = [
    ("1 · Pared principal (elige una)",
     "La pared grande con la ventana de la OLED, el pulsador DISPLAY, el XT60, el interruptor y la ranura de "
     "los cables de los sensores. Las cinco tienen los mismos insertos y encajan igual con la base y la tapa: "
     "solo cambian el logo y los LEDs.",
     [("pared_multicolor", ["pared_multicolor_bambu.3mf", "pared_multicolor.3mf"], "A · Pared con logo en 4 colores",
       "Pared sin agujeros de LEDs, logo marino, azul y gris incrustado a ras.",
       "Tienes AMS (o cualquier multimaterial) y no te interesa ver los LEDs de la placa.",
       "Cara del logo sobre la cama. AMS: 1 blanco, 2 marino, 3 azul, 4 gris. `_bambu.3mf` para Bambu Studio; "
       "el `.3mf` genérico para otros laminadores."),
      ("pared_monocolor", ["pared_monocolor.stl"], "B · Pared de un color",
       "La misma pared, con el logo grabado 1 mm en vez de incrustado.",
       "No tienes AMS y no necesitas los LEDs. La más sencilla de imprimir.",
       "Cara del logo sobre la cama, un solo filamento."),
      ("pared_led_multicolor", ["con_leds/pared_led_multicolor_bambu.3mf", "con_leds/pared_led_multicolor.3mf"],
       "C · Pared con LEDs, logo en 4 colores",
       "Un agujero sobre cada uno de los 10 LEDs de la placa de la Pico (VL1–VL4, US1–US5, PWR), con un tubo "
       "por dentro hasta el LED y su nombre al lado. El logo baja, entre la ventana de la OLED y el XT60.",
       "Quieres ver desde fuera qué sensores están activos y tienes AMS.",
       "Cara del logo sobre la cama. AMS: 1 blanco, 2 marino, 3 azul, 4 gris. Necesita las lentillas."),
      ("pared_led_sin_ams", ["sin_ams/pared_led_sin_ams.stl"], "D · Pared con LEDs sin AMS",
       "La pared C con el logo y los nombres en hueco de 1,5 mm, para rellenarlos con piezas impresas aparte. "
       "Tubos, lentillas e insertos iguales que en C.",
       "Quieres los LEDs y el logo en colores, pero tu impresora no tiene AMS.",
       "Blanco, cara del logo sobre la cama. Necesita los 3 rellenos y las lentillas."),
      ("rellenos", ["sin_ams/relleno_marino.stl", "sin_ams/relleno_azul.stl", "sin_ams/relleno_gris.stl"],
       "D · Rellenos del logo y los nombres",
       "Marino: «ROS» y los nombres de los conectores. Azul: «2D2» y los 12 puntos. Gris: el marco de los puntos. "
       "Tienen 0,1 mm de holgura por lado y quedan a ras de la pared.",
       "Solo con la pared D.",
       "Una placa por color, cara vista sobre la cama, capas de 0,1–0,15 mm, sin borde. Salen en su sitio y en "
       "espejo: dales la vuelta, mételos en su hueco y fíjalos con una gota de cianoacrilato."),
      ("pared_led_monocolor", ["con_leds/pared_led_monocolor.stl"], "E · Pared con LEDs de un color",
       "La pared C con el logo y los nombres grabados 1 mm.",
       "Quieres los LEDs, no tienes AMS y un solo color te vale.",
       "Cara del logo sobre la cama, un solo filamento. Necesita las lentillas."),
      ("lentes_led", ["con_leds/lentes_led.stl"], "Lentillas de los LEDs",
       "12 discos (10 y 2 de repuesto) que se meten a presión en la boca de cada tubo, a ras de la pared.",
       "Con cualquier pared con LEDs: C, D o E.",
       "PLA translúcido (o PETG transparente), discos planos sobre la cama."),
      ]),
    ("2 · Piezas comunes (siempre)", "Las mismas con cualquier pared.",
     [("base", ["base.stl"], "Base", "Suelo, trasera, tabique central (Pi y convertidor) y orejetas de fijación.",
       "Siempre.", "Suelo sobre la cama."),
      ("tapa", ["tapa.stl"], "Tapa", "Techo, lateral y frontal estrecho en una pieza que baja desde arriba.",
       "Siempre.", "Techo sobre la cama."),
      ("pulsador", ["pulsador.stl"], "Varilla del pulsador DISPLAY",
       "Atraviesa la pared y pulsa el botón DISPLAY de la placa de la Pico.", "Siempre.", "De pie."),
      ]),
    ("3 · Marco trasero (elige uno)",
     "Cierra la ventana de la trasera alrededor de los USB y el Ethernet de la Pi. La Pi 4 y la Pi 5 tienen "
     "esos conectores al revés, por eso hay dos.",
     [("marco_pi4", ["marco_pi4.stl"], "Marco para la Pi 4", "Ethernet arriba, USB abajo.",
       "Si montas una Raspberry Pi 4.", "Cara exterior sobre la cama."),
      ("marco_pi5", ["marco_pi5.stl"], "Marco para la Pi 5", "Ethernet abajo, USB arriba.",
       "Si montas una Raspberry Pi 5.", "Cara exterior sobre la cama."),
      ]),
    ("4 · HDMI trasero (opcional)",
     "La base ya trae la ventana del HDMI y dos insertos M3. Según lo que pongas ahí:",
     [("soporte_hdmi", ["soporte_hdmi.stl"], "Soporte HDMI para kit FPC",
       "Capucha que sujeta la placa «A hembra» de un kit HDMI FPC (de FPV): clavija micro-HDMI a 90°, cinta plana "
       "y placa HDMI A hembra. La cinta entra por la ventana y va bajo la Pi hasta su HDMI 0.",
       "Usas el kit HDMI FPC. Mide la placa A hembra antes de imprimir (`fpc_a` en `hdmi_fpc.scad`).",
       "Cara exterior sobre la cama, capucha hacia arriba. 2 × M3 × 8 avellanados."),
      ("tapa_hdmi", ["tapa_hdmi.stl"], "Tapa HDMI ciega", "Tapa la ventana del HDMI con un tapón que la rellena.",
       "No pones HDMI.", "Cara exterior sobre la cama. 2 × M3 × 8 avellanados."),
      ]),
]
HDMI_NOTE = ("Si usas un **HDMI hembra de panel con brida y 2 tornillos M3**, no hace falta imprimir nada: se "
             "atornilla directamente a los insertos de la base.")

NOT_TO_PRINT = [
    ("`pared.stl`, `logo_marino.stl`, `logo_azul.stl`, `logo_gris.stl`",
     "Son las 4 partes que van dentro de `pared_multicolor*.3mf`. Úsalas solo para montar tu propio proyecto "
     "multicolor en un laminador que no lea el 3MF."),
    ("`con_leds/pared_led.stl`, `con_leds/logo_*_led.stl`", "Lo mismo para `pared_led_multicolor*.3mf`."),
]


# --- output ---------------------------------------------------------------------------------------------
def render_images():
    IMG.mkdir(exist_ok=True)
    for name, cam in VIEWS.items():
        r = subprocess.run([OPENSCAD, "-o", str(IMG / f"{name}.png"), "-D", f'pieza="{name}"', "--imgsize=1200,900",
                            f"--camera=0,0,0,{cam},0", "--viewall", "--autocenter", "--colorscheme=Tomorrow",
                            str(HERE / "piezas.scad")], capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        if r.returncode or "ERROR" in out or "WARNING" in out:
            raise RuntimeError(f"{name}: {out[-1500:]}")
        print("ok", name, flush=True)


def files_md(files):
    return " · ".join(f"`stl/{f}`" for f in files)


def write_md(path):
    L = ['<img src="../../../media/ros2d2-logo.png" alt="ROS2D2" width="360"> '
         '<img src="../../../ros2_ws/src/r2_web/www/astromech-spain-logo.png" alt="Astromech Spain" width="90">', "",
         f"# {TITLE}", "", INTRO, "", f"**Versión al día:** <{REPO_URL}>", "",
         "## Qué imprimir", ""]
    L += [f"- {c}" for c in CHECKLIST]
    L += ["", "### ¿Qué pared?", "", "| " + " | ".join(DECIDE_HEAD) + " |", "|---|---|---|"]
    L += ["| " + " | ".join(r) + " |" for r in DECIDE]
    L += ["", GENERAL]
    for title, intro, pieces in SECTIONS:
        L += ["", f"## {title}", "", intro]
        for img, files, name, what, when, how in pieces:
            L += ["", f"### {name}", "", f'<img src="img/{img}.png" alt="{name}" width="480">', "",
                  f"**Ficheros:** {files_md(files)}", "", f"**Qué es:** {what}", "", f"**Cuándo:** {when}", "",
                  f"**Cómo imprimir:** {how}"]
        if title.startswith("4"):
            L += ["", HDMI_NOTE]
    L += ["", "## Ficheros que no hay que imprimir sueltos", "", "| Fichero | Para qué está |", "|---|---|"]
    L += [f"| {f} | {w} |" for f, w in NOT_TO_PRINT]
    path.write_text("\n".join(L) + "\n", encoding="utf8")
    print("ok", path.name, flush=True)


def md_inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def write_html(path):
    e = md_inline
    rows = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in DECIDE)
    body = ""
    for title, intro, pieces in SECTIONS:
        body += f"<h2 class=sec>{e(title)}</h2><p>{e(intro)}</p>"
        for img, files, name, what, when, how in pieces:
            body += (f"<section class=card><img src='{(IMG / f'{img}.png').as_uri()}'><div><h3>{e(name)}</h3>"
                     f"<p class=files>{e(files_md(files))}</p><p><b>Qué es:</b> {e(what)}</p>"
                     f"<p><b>Cuándo:</b> {e(when)}</p><p><b>Cómo imprimir:</b> {e(how)}</p></div></section>")
        if title.startswith("4"):
            body += f"<p class=note>{e(HDMI_NOTE)}</p>"
    skip = "".join(f"<tr><td>{e(f)}</td><td>{e(w)}</td></tr>" for f, w in NOT_TO_PRINT)
    doc = f"""<!doctype html><html lang=es><meta charset=utf-8><title>{html.escape(TITLE)}</title>
<style>
@page {{ size: A4; margin: 12mm 12mm 16mm;
  @bottom-left {{ content: "ROS2D2 · versión al día: {REPO_URL}"; font: 8pt Segoe UI, Arial, sans-serif; color: #555; }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font: 8pt Segoe UI, Arial, sans-serif; color: #555; }} }}
body {{ font-family: Segoe UI, Arial, sans-serif; color: #1d1d1f; font-size: 10pt; }}
h1 {{ font-size: 19pt; margin: 0 0 3mm; }} h2 {{ font-size: 13pt; margin: 5mm 0 2mm; }} h3 {{ font-size: 11.5pt; margin: 0 0 1.5mm; }}
.logos {{ display: flex; align-items: center; justify-content: space-between; margin: 0 0 4mm; }}
.logos .r {{ height: 15mm; }} .logos .a {{ height: 24mm; }}
.latest {{ border: 1.5px solid #2a6fdb; border-radius: 2mm; padding: 2mm 3mm; margin: 3mm 0; }} .latest a {{ color: #2a6fdb; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 3mm; }}
td, th {{ border-bottom: 1px solid #ddd; padding: 1.2mm 2mm; text-align: left; vertical-align: top; }}
th {{ background: #f0f2f5; }}
.sec {{ page-break-before: always; }} .sec:first-of-type {{ page-break-before: auto; }}
.card {{ display: flex; gap: 4mm; border: 1.2px solid #bbb; border-radius: 2.5mm; padding: 3mm; margin: 0 0 4mm;
        page-break-inside: avoid; }}
.card img {{ width: 70mm; height: 52mm; object-fit: contain; flex: none; }}
.card p {{ margin: 0 0 1.4mm; }} .files {{ color: #2a4f9b; }} code {{ font-size: 8.8pt; }}
.note {{ border-left: 3px solid #2a6fdb; padding: 1mm 3mm; }}
</style>
<div class=logos><img class=r src='{LOGO_ROS2D2.as_uri()}' alt="ROS2D2"><img class=a src='{LOGO_ASTROMECH.as_uri()}' alt="Astromech Spain"></div>
<h1>{html.escape(TITLE)}</h1><p>{e(INTRO)}</p>
<div class=latest><b>Versión al día:</b> <a href='{REPO_URL}'>{REPO_URL}</a></div>
<h2>Qué imprimir</h2><ul>{''.join(f'<li>{e(c)}</li>' for c in CHECKLIST)}</ul>
<h3>¿Qué pared?</h3><table><tr>{''.join(f'<th>{html.escape(h)}</th>' for h in DECIDE_HEAD)}</tr>{rows}</table>
<p>{e(GENERAL)}</p>
{body}
<h2>Ficheros que no hay que imprimir sueltos</h2><table><tr><th>Fichero</th><th>Para qué está</th></tr>{skip}</table>
</html>"""
    path.write_text(doc, encoding="utf8")


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
    write_md(HERE / "GUIA_IMPRESION.md")
    with tempfile.TemporaryDirectory() as tmp:
        h = pathlib.Path(tmp) / "guia.html"
        write_html(h)
        print_pdf(h, HERE / "GUIA_IMPRESION.pdf")


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv[1:])
