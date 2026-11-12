# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Assembly guide of the rack box (option C), IKEA style, Spanish and English, with its BOM.

    python -I hardware/caja_ros2_rack/build_docs.py [--no-images]

The generator is the first box's (hardware/caja_ros2/build_docs.py); this file only gives it the
rack box's views, steps, parts and texts. BOM and step hardware come from this box's fasteners.scad.
"""
import copy
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("docs_ros2", HERE.parent / "caja_ros2" / "build_docs.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

g.HERE = HERE
g.IMG = HERE / "montaje" / "img"
g.VIEWS = {
    "montada": ('scene="montada"', 62, 320),
    "montada_atras": ('scene="montada_atras"', 58, 140),
    "montada_led": ('scene="montada";leds=true', 75, 270),
    "interior": ('scene="abierta"', 55, 40),
    "despiece": ('scene="despiece"', 60, 330),
    "paso1": ('scene="paso";step=1', 55, 330),
    "paso2": ('scene="paso";step=2', 55, 40),
    "paso3": ('scene="paso";step=3', 55, 40),
    "paso4": ('scene="paso";step=4', 60, 300),
    "paso5": ('scene="paso";step=5', 55, 60),
    "paso6": ('scene="paso";step=6', 60, 320),
    "paso7": ('scene="paso";step=7', 55, 40),
    "paso8": ('scene="paso";step=8', 55, 140),
}
g.PRINTED = [
    ("pared_multicolor_bambu.3mf", "Pared principal con el logo en 4 colores (AMS: blanco, marino, azul, gris)",
     "Main face with the logo in 4 colours (AMS: white, navy, blue, grey)"),
    ("pared_monocolor.stl", "o bien: pared principal de un color, logo grabado", "or: single-colour main face, engraved logo"),
    ("con_leds/pared_led_multicolor_bambu.3mf", "o bien: pared con un agujero sobre cada LED de la placa de la Pico, logo abajo y "
     "nombres de los conectores (AMS: blanco, marino, azul, gris)", "or: main face with a hole over each LED of the Pico "
     "board, logo lower down and the connector names (AMS: white, navy, blue, grey)"),
    ("con_leds/pared_led_monocolor.stl", "o bien: la pared con LEDs de un color, logo y nombres grabados",
     "or: the LED face in one colour, logo and names engraved"),
    ("con_leds/guias_luz.stl", "Guías de luz (opcional, solo con la pared con LEDs): una pieza de PLA translúcido (o PETG "
     "transparente), extremos exteriores sobre la cama, relleno 100 %", "Light pipes (optional, only with the LED "
     "face): one piece in translucent PLA (or clear PETG), outer ends on the bed, 100 % infill"),
    ("con_leds/prueba_luz.stl", "Barra de prueba de luz: imprímela antes y ponla sobre un LED encendido para ver si tu "
     "filamento deja pasar bastante luz", "Light test rod: print it first and hold it on a lit LED to see whether "
     "your filament lets enough light through"),
    ("base.stl", "Base: suelo, trasera, tabique central", "Base: floor, back, central divider"),
    ("tapa.stl", "Tapa (techo + lateral + frontal estrecho)", "Shell (roof + side + narrow front)"),
    ("marco_pi4.stl", "Marco trasero para la Pi 4 (Ethernet arriba)", "Back frame for the Pi 4 (Ethernet at the top)"),
    ("marco_pi5.stl", "o bien: marco trasero para la Pi 5 (Ethernet abajo)", "or: back frame for the Pi 5 (Ethernet at the bottom)"),
    ("pulsador.stl", "Varilla del pulsador DISPLAY", "DISPLAY push rod"),
]
g.STEPS = [
    {"n": 1,
     "es": {"title": "Insertos térmicos", "text": "Con el soldador a unos 220 °C mete los insertos rectos y a ras. En la "
            "pared principal, 7 M3: 4 en las columnas, 2 en las pestañas de abajo y 1 en la de arriba; y 2 M3 más por "
            "fuera, en los agujeros del XT60. En la base, 10 M3: 2 en lo alto del tabique, 2 en el tabique para el "
            "convertidor, 2 en los bloques del suelo y 4 por fuera de la trasera (2 del marco, 2 del HDMI); y los 4 M2,5 "
            "en las columnas de la Pi."},
     "en": {"title": "Heat-set inserts", "text": "With the iron at about 220 °C press the inserts in straight and flush. On "
            "the main face, 7 M3: 4 in the columns, 2 in the bottom tabs and 1 in the top tab; plus 2 M3 from outside in "
            "the XT60's holes. On the base, 10 M3: 2 on top of the divider, 2 in the divider for the converter, 2 in the "
            "floor blocks and 4 from outside the back (2 for the frame, 2 for the HDMI); and the 4 M2.5 in the Pi's "
            "standoffs."}},
    {"n": 2,
     "es": {"title": "Convertidor al tabique, arriba", "text": "De pie, arriba del todo, con la base contra el tabique, las "
            "aletas hacia fuera y los cables hacia delante: van por el hueco de arriba del tabique al lado de la Pico. "
            "Así su calor sube y sale por el techo sin pasar por la Pi. Comprueba antes con el calibre sus agujeros "
            "(`conv_holes`)."},
     "en": {"title": "Converter onto the divider, high", "text": "On edge, at the very top, its base plate against the "
            "divider, fins outwards, wires to the front: they go through the top pass in the divider to the Pico side. "
            "Its heat rises out of the roof without passing the Pi. Check its holes (`conv_holes`) with a caliper first."}},
    {"n": 3,
     "es": {"title": "Raspberry Pi, marco y HDMI", "text": "Pi 4 o Pi 5 sobre sus 4 columnas, abajo, con los USB y el "
            "Ethernet en la ventana de la trasera y el USB-C abajo. Pincha el USB-C acodado (5 V del convertidor, bajando "
            "por delante de la Pi) y el micro-HDMI acodado en el HDMI 0; ese cable pasa bajo la Pi por el hueco de abajo "
            "del tabique. Atornilla desde fuera el marco de tu Pi (`marco_pi4` o `marco_pi5`) y el conector HDMI de panel."},
     "en": {"title": "Raspberry Pi, frame and HDMI", "text": "Pi 4 or Pi 5 on its 4 standoffs, low down, USB and Ethernet "
            "in the back window, USB-C at the bottom. Plug in the angled USB-C (5 V from the converter, down in front of the "
            "Pi) and the angled micro-HDMI into HDMI 0; that cable runs under the Pi through the divider's bottom pass. "
            "Screw on, from outside, the frame for your Pi (`marco_pi4` or `marco_pi5`) and the HDMI panel jack."}},
    {"n": 4,
     "es": {"title": "XT60 e interruptor en la pared principal", "text": "Desde fuera, abajo: el XT60E-F girado, con 2 "
            "tornillos a los insertos, y el interruptor a presión."},
     "en": {"title": "XT60 and switch on the main face", "text": "From outside, low down: the XT60E-F turned on its side "
            "with 2 screws into the inserts, and the switch snapped in."}},
    {"n": 5,
     "es": {"title": "Varilla y placa de la Pico", "text": "Con la pared con LEDs, las guías de luz son opcionales "
            "(sin ellas los LEDs se ven por los agujeros). Si las pones, van antes de colgar la placa: desde dentro, mete "
            "las 10 barras por sus agujeros y empuja el marco contra la pared hasta que los 4 ganchos encajen. Mete la "
            "varilla desde dentro por su guía. Antes de atornillar, presenta la placa sin tornillos sobre las 4 columnas, "
            "componentes hacia la pared: debe asentar en las cuatro sin balancearse; si se balancea, alguna barra toca "
            "su LED: lija la punta. Luego atorníllala. Para sacarla, abre los ganchos de dos en dos con un destornillador "
            "pequeño. Si algún día usas J4 (EXP), su cable rodea la barra PWR. Aprieta los 5 V en el borne J1, pincha el micro-USB acodado en "
            "la Pico y conecta los sensores: sus cables salen por la ranura de arriba."},
     "en": {"title": "Push rod and Pico board", "text": "With the LED face, the light pipes are optional (without "
            "them the LEDs show through the holes). If you fit them, they go in before hanging the board: from inside, "
            "slide the 10 rods into their holes and push the frame against the wall until the 4 hooks click. Slide the "
            "rod into its guide from inside. Before screwing, offer the board up without screws onto the 4 columns, parts "
            "towards the wall: it must sit on all four without rocking; if it rocks, a rod touches its LED: sand its "
            "tip. Then screw it on. To take it out, open the hooks two at a time with a small screwdriver. If you ever "
            "use J4 (EXP), its cable goes round the PWR rod. Tighten the 5 V in terminal J1, plug the angled micro-USB into the "
            "Pico and connect the sensors: their cables leave through the slot at the top."}},
    {"n": 6,
     "es": {"title": "Pared principal a la base", "text": "Los 24 V (XT60 → interruptor → convertidor) suben por delante "
            "de la placa de la Pico y cruzan por el hueco de arriba del tabique; los 5 V del borne J1 vuelven por el mismo "
            "hueco y por encima de la placa. Atornilla la pared desde debajo del suelo."},
     "en": {"title": "Main face onto the base", "text": "The 24 V (XT60 → switch → converter) run up in front of the Pico "
            "board and cross through the divider's top pass; the 5 V to terminal J1 come back through the same pass and "
            "over the board. Screw the face on from under the floor."}},
    {"n": 7,
     "es": {"title": "Tapa", "text": "Bájala desde arriba y pon los 3 tornillos del techo y los 2 del lateral. El aire "
            "entra por las rejillas de abajo (frontal y lateral, junto a la Pi) y sale por las de arriba y el techo."},
     "en": {"title": "Shell", "text": "Lower it from above and fit the 3 roof screws and the 2 side screws. Air comes in "
            "through the low vents (front and side, by the Pi) and leaves through the high ones and the roof."}},
    {"n": 8,
     "es": {"title": "USB y fijación al R2", "text": "Saca el micro-USB por la muesca de la trasera y enchúfalo en un USB de "
            "la Pi. Atornilla la caja al R2 por sus 4 orejetas."},
     "en": {"title": "USB and onto the R2", "text": "Bring the micro-USB out of the notch in the back into a Pi USB port. "
            "Screw the box to the R2 through its 4 ears."}},
]
g.NAMES = dict(g.NAMES, ins_m25=("Inserto térmico M2,5 (5 mm de largo, agujero de 3,6 mm)", "M2.5 heat-set insert (5 mm long, 3.6 mm hole)"),
               m25x6=("Tornillo M2.5 × 6", "M2.5 × 6 screw"))
g.SHORT = dict(g.SHORT, ins_m25="inserto M2,5")
g.SHORT_EN = dict(g.SHORT_EN, ins_m25="M2.5 insert")
g.OTHER = [o for o in g.OTHER if "USB-C" not in o[1]] + [
    ("1", "Cable USB-C macho con hilos (5 V a la Pi), acodado 90° arriba/abajo, 15–20 cm; 3 A para la Pi 4, 5 A para la Pi 5",
     "USB-C male pigtail (5 V to the Pi), 90° up/down angle, 15–20 cm; 3 A for a Pi 4, 5 A for a Pi 5"),
    ("1", "Cable micro-HDMI macho acodado 90° a HDMI hembra de panel con 2 tornillos M3, 30 cm (mide su brida: `hdmi_*`)",
     "Angled 90° micro-HDMI male to HDMI female panel-mount cable with 2 M3 screws, 30 cm (measure its flange: `hdmi_*`)"),
]
g.TXT = copy.deepcopy(g.TXT)
g.TXT["es"].update(title="Caja ROS2 rack · Instrucciones de montaje", intro=
    "Segunda caja, tipo rack: la placa de la Pico, la Pi y el convertidor van de pie, en paralelo. 78 × 95 × 145 mm "
    "(1,07 L). La Pi va abajo y el convertidor arriba, para que su calor no suba hacia la Pi. Vale para la Pi 4 y la "
    "Pi 5: solo cambia el marco de la trasera. La OLED, el logo, el interruptor y el XT60 están en la pared principal; "
    "los USB de la Pi y un HDMI de panel, detrás. Todo va atornillado a insertos. Antes de imprimir mide lo que indica "
    "el README.")
g.TXT["en"].update(title="ROS2 rack box · Assembly instructions", intro=
    "Second box, rack style: the Pico board, the Pi and the converter stand on edge, side by side. 78 × 95 × 145 mm "
    "(1.07 L). The Pi sits low and the converter high, so its heat does not rise into the Pi. It takes a Pi 4 or a "
    "Pi 5: only the back frame changes. OLED, logo, switch and XT60 are on the main face; the Pi's USB and an HDMI "
    "panel jack at the back. Every screw goes into an insert. Before printing, measure what the README lists.")
g.BOX_DIMS = (78, 95, 145)
g.WIRING = copy.deepcopy(g.WIRING)
g.WIRING["es"].update(slot="ranura lateral", back="pared principal", pi="Raspberry Pi 4 / Pi 5",
                      micro="micro-USB acodado: sale por la muesca trasera y entra en un USB de la Pi")
g.WIRING["en"].update(slot="side slot", back="main face", pi="Raspberry Pi 4 / Pi 5",
                      micro="angled micro-USB: out of the back notch into a Pi USB port")

STEPS, bom, fastener_table, write_guide, wiring_svg = g.STEPS, g.bom, g.fastener_table, g.write_guide, g.wiring_svg


def main(images=True):
    g.IMG.mkdir(parents=True, exist_ok=True)
    for lang in ("es", "en"):           # same angled plugs as the first box
        shutil.copy(HERE.parent / "caja_ros2" / "montaje" / "img" / f"conectores_{lang}.svg", g.IMG / f"conectores_{lang}.svg")
    g.main(images)


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv)
