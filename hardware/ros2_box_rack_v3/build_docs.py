# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Assembly guide of the rack box, IKEA style, Spanish and English, with its BOM.

    python -I hardware/ros2_box_rack_v3/build_docs.py [--no-images]

The generator is docs_core.py; this file only gives it the
rack box's views, steps, parts and texts. BOM and step hardware come from this box's fasteners.scad.
"""
import copy
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("docs_ros2", HERE / "docs_core.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

g.HERE = HERE
g.IMG = HERE / "assembly" / "img"
g.VIEWS = {
    "assembled": ('scene="assembled"', 62, 320),
    "assembled_back": ('scene="assembled_back"', 58, 140),
    "assembled_led": ('scene="assembled";leds=true', 75, 270),
    "interior": ('scene="abierta"', 55, 40),
    "exploded": ('scene="exploded"', 60, 330),
    "step1": ('scene="step";step=1', 55, 330),
    "step1_pi": ('scene="step";step=1', 55, 60),        # Pi side: the M2.5 inserts
    "step2": ('scene="step";step=2', 55, 40),
    "step3": ('scene="step";step=3', 55, 40),
    "step4": ('scene="step";step=4', 60, 300),
    "step5": ('scene="step";step=5', 55, 60),
    "step6": ('scene="step";step=6', 60, 320),
    "step7": ('scene="step";step=7', 55, 40),
    "step8": ('scene="step";step=8', 55, 140),
}
g.PRINTED = [
    ("wall_multicolor_bambu.3mf", "Pared principal con el logo en 4 colores (AMS: blanco, marino, azul, gris)",
     "Main face with the logo in 4 colours (AMS: white, navy, blue, grey)"),
    ("wall_monocolor.stl", "o bien: pared principal de un color, logo grabado", "or: single-colour main face, engraved logo"),
    ("leds/wall_led_multicolor_bambu.3mf", "o bien: pared con un agujero sobre cada LED de la placa de la Pico y otro "
     "sobre el de la Pico (AMS: blanco, marino, azul, gris)", "or: main face with a hole over each LED of the Pico "
     "board and one over the Pico's own (AMS: white, navy, blue, grey)"),
    ("leds/wall_led_monocolor.stl", "o bien: la pared con LEDs de un color, logo grabado",
     "or: the LED face in one colour, logo engraved"),
    ("no_ams/wall_led_no_ams.stl", "o bien: la pared con LEDs sin AMS, logo en hueco de 1,4 mm, con "
     "sus 3 rellenos (no_ams/inlay_navy.stl, inlay_blue.stl, inlay_grey.stl) impresos aparte y pegados",
     "or: the LED face without AMS, logo as 1.4 mm pockets, with its 3 fillings "
     "(no_ams/inlay_navy.stl, inlay_blue.stl, inlay_grey.stl) printed apart and glued in"),
    ("leds/led_lenses.stl", "Lentillas de los LEDs (solo con la pared con LEDs): 13 discos de PLA translúcido (o PETG "
     "transparente), 11 y 2 de repuesto, planos sobre la cama", "LED lenses (only with the LED face): 13 discs in "
     "translucent PLA (or clear PETG), 11 and 2 spares, flat on the bed"),
    ("base.stl", "Base: suelo, frontal (XT60, interruptor), trasera, tabique central y rebajes de las orejas",
     "Base: floor, front (XT60, switch), back, central divider and the ear pockets"),
    ("shell.stl", "Tapa (techo + lateral)", "Shell (roof + side)"),
    ("ear.stl", "5 orejas de fijación (4 y 1 de repuesto), de canto", "5 mounting ears (4 and 1 spare), on edge"),
    ("ear_blank.stl", "4 tapas ciegas para los rebajes sin oreja", "4 blanks for the pockets without an ear"),
    ("frame_pi4.stl", "Marco trasero para la Pi 4 (Ethernet arriba)", "Back frame for the Pi 4 (Ethernet at the top)"),
    ("frame_pi5.stl", "o bien: marco trasero para la Pi 5 (Ethernet abajo)", "or: back frame for the Pi 5 (Ethernet at the bottom)"),
    ("push_rod.stl", "Varilla del pulsador DISPLAY", "DISPLAY push rod"),
]
g.STEPS = [
    {"n": 1, "extra_views": ["step1_pi"],
     "es": {"title": "Insertos térmicos", "text": "Con el soldador a unos 220 °C mete los insertos rectos y a ras. Hay "
            "dos tamaños y no se cambian entre sí: 34 M3 (5,7 mm de largo, agujero de 4,0 mm) y 4 M2,5 (5 mm de largo, "
            "agujero de 3,6 mm), que son los pequeños. En el dibujo, los M3 en dorado y los M2,5 en rojo.",
            "list": ["**M3** · pared principal, por dentro (8): 4 en las columnas de la placa de la Pico, 2 en las "
                     "pestañas de abajo y 2 en las de arriba.",
                     "**M3** · base, por dentro (6): 2 en lo alto del tabique, 2 en el tabique para el convertidor y 2 "
                     "en los bloques del suelo.",
                     "**M3** · trasera de la base, por fuera (4): 2 del marco de la Pi y 2 del HDMI.",
                     "**M3** · rebajes de las orejas, por fuera (16): 2 en cada uno de los 8 rebajes, 4 en la frontal y "
                     "4 en la trasera.",
                     "**M2,5** · base (4): las 4 columnas de la Pi. Son los únicos M2,5 de la caja."]},
     "en": {"title": "Heat-set inserts", "text": "With the iron at about 220 °C press the inserts in straight and flush. "
            "There are two sizes and they don't swap: 34 M3 (5.7 mm long, 4.0 mm hole) and 4 M2.5 (5 mm long, 3.6 mm "
            "hole), the small ones. In the picture, M3 in gold and M2.5 in red.",
            "list": ["**M3** · main face, inside (8): 4 in the Pico board's columns, 2 in the bottom tabs and 2 in the "
                     "top ones.",
                     "**M3** · base, inside (6): 2 on top of the divider, 2 in the divider for the converter and 2 in "
                     "the floor blocks.",
                     "**M3** · back of the base, outside (4): 2 for the Pi's frame and 2 for the HDMI.",
                     "**M3** · ear pockets, outside (16): 2 in each of the 8 pockets, 4 on the front and 4 on the back.",
                     "**M2.5** · base (4): the Pi's 4 standoffs. They are the box's only M2.5."]}},
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
            "del tabique. Atornilla desde fuera el marco de tu Pi (`frame_pi4` o `frame_pi5`) y el conector HDMI de panel."},
     "en": {"title": "Raspberry Pi, frame and HDMI", "text": "Pi 4 or Pi 5 on its 4 standoffs, low down, USB and Ethernet "
            "in the back window, USB-C at the bottom. Plug in the angled USB-C (5 V from the converter, down in front of the "
            "Pi) and the angled micro-HDMI into HDMI 0; that cable runs under the Pi through the divider's bottom pass. "
            "Screw on, from outside, the frame for your Pi (`frame_pi4` or `frame_pi5`) and the HDMI panel jack."}},
    {"n": 4,
     "es": {"title": "XT60 e interruptor en la frontal", "text": "En la frontal estrecha, que es parte de la base, en el lado "
            "de la Pi: el XT60 macho, justo encima de la Pi, desde dentro, con su frontal asomando por el hueco y la brida "
            "contra la frontal. Pon los 2 tornillos M3 desde fuera, por los agujeros pasantes y la brida, hasta las tuercas "
            "de detrás. Arriba del todo, el interruptor entra a presión desde fuera. Suelda y aísla antes sus cables: "
            "detrás hay poco fondo y se doblan nada más salir."},
     "en": {"title": "XT60 and switch on the front", "text": "On the narrow front, which is part of the base, on the Pi's "
            "side: the male XT60, just above the Pi, from inside, its front showing through the opening and its flange "
            "against the front. Fit the 2 M3 screws from outside, through the holes and the flange, into the nuts behind. "
            "At the very top, the switch snaps in from outside. Solder and insulate their wires first: there is little "
            "depth behind them and they bend as soon as they come out."}},
    {"n": 5,
     "es": {"title": "Varilla y placa de la Pico", "text": "Con la pared con LEDs, mete desde fuera una lentilla en cada "
            "uno de los 11 agujeros (el de arriba, junto al USB, es el LED de la propia Pico y no lleva tubo), el tetón "
            "dentro, hasta que quede a ras; si alguna baila, una gota de pegamento. Mete la "
            "varilla desde dentro por su guía. Antes de atornillar, presenta la placa sin tornillos sobre las 4 columnas, "
            "componentes hacia la pared: debe asentar en las cuatro sin balancearse; si se balancea, algún tubo toca "
            "su LED: lija la punta. Luego atorníllala. Si algún día usas J4 (EXP), su cable rodea el tubo PWR. Aprieta los 5 V en el borne J1 y pincha el micro-USB recto en "
            "la Pico: sube recto y se dobla bajo el techo hacia la trasera. Los sensores se conectan después, desde fuera, "
            "por las bahías de la cara."},
     "en": {"title": "Push rod and Pico board", "text": "With the LED face, press a lens into each of the 11 holes "
            "from outside (the top one, by the USB, is the Pico's own LED and has no tube), its stem in, until it sits flush; if one is loose, a drop of glue. Slide the "
            "rod into its guide from inside. Before screwing, offer the board up without screws onto the 4 columns, parts "
            "towards the wall: it must sit on all four without rocking; if it rocks, a tube touches its LED: sand its "
            "tip. Then screw it on. If you ever "
            "use J4 (EXP), its cable goes round the PWR tube. Tighten the 5 V in terminal J1 and plug the straight micro-USB into the "
            "Pico: it goes straight up and bends under the roof towards the back. The sensors plug in later, from outside, "
            "through the face's bays."}},
    {"n": 6,
     "es": {"title": "Pared principal a la base", "text": "Los 24 V (XT60 → interruptor → convertidor) se quedan en el lado "
            "de la Pi, junto a la frontal; los 5 V al borne J1 cruzan por el hueco de arriba del tabique y por encima de "
            "la placa. Atornilla la pared desde debajo del suelo."},
     "en": {"title": "Main face onto the base", "text": "The 24 V (XT60 → switch → converter) stay on the Pi's side, by "
            "the front; the 5 V to terminal J1 cross through the divider's top pass and over the board. Screw the face on from under the floor."}},
    {"n": 7,
     "es": {"title": "Tapa", "text": "Es el techo y el lateral: la frontal se queda con la base. Bájala "
            "desde arriba y pon los 4 tornillos del techo y los 2 del lateral. El aire "
            "entra por las rejillas de abajo (frontal y lateral, junto a la Pi) y sale por las de arriba y el techo."},
     "en": {"title": "Shell", "text": "It is the roof and the side: the front stays with the base. Lower "
            "it from above and fit the 4 roof screws and the 2 side screws. Air comes in "
            "through the low vents (front and side, by the Pi) and leaves through the high ones and the roof."}},
    {"n": 8,
     "es": {"title": "USB, orejas y fijación al R2", "text": "Saca el micro-USB por la muesca de la trasera, bájalo por fuera y enchufa su USB-A en un USB "
            "de la Pi: es el conector que se ve fuera de la caja en el dibujo (no está suelto). Por él la Pi recibe los sensores y flashea el firmware de la Pico. "
            "Elige cómo va la caja: de pie, con las 4 orejas en los rebajes junto al suelo, o tumbada sobre el lateral de "
            "la tapa, con las 4 en los rebajes junto a ese lateral. Cada oreja va a ras en su rebaje con 2 M3 × 8 "
            "avellanados; en los otros 4 rebajes, una tapa ciega con sus 2 tornillos. Luego atornilla la caja al R2 por "
            "las 4 lengüetas."},
     "en": {"title": "USB, ears and onto the R2", "text": "Bring the micro-USB out of the notch in the back, down the outside, and plug its USB-A into a Pi "
            "USB port: it is the plug you see outside the box in the picture (it is not loose). Through it the Pi gets the sensor data and flashes the Pico firmware. "
            "Choose how the box sits: standing, with the 4 ears in the pockets by the floor, or lying on the shell's "
            "side, with the 4 in the pockets by that side. Each ear sits flush in its pocket with 2 M3 × 8 countersunk; "
            "the other 4 pockets take a blank with its 2 screws. Then screw the box to the R2 through the 4 lugs."}},
]
g.NAMES = dict(g.NAMES, ins_m25=("Inserto térmico M2,5 (5 mm de largo, agujero de 3,6 mm)", "M2.5 heat-set insert (5 mm long, 3.6 mm hole)"),
               m25x6=("Tornillo M2.5 × 6", "M2.5 × 6 screw"))
g.SHORT = dict(g.SHORT, ins_m25="inserto M2,5")
g.SHORT_EN = dict(g.SHORT_EN, ins_m25="M2.5 insert")
g.OTHER = [o for o in g.OTHER if "USB-C" not in o[1] and "micro-USB" not in o[1] and "Pasacables" not in o[1]] + [
    ("1", "Cable micro-USB 2.0 a USB-A con clavija recta, unos 30 cm (ver «Conectores»)",
     "micro-USB 2.0 to USB-A cable with a straight plug, about 30 cm (see «Plugs»)"),
    ("1", "Cable USB-C macho con hilos (5 V a la Pi), acodado 90° arriba/abajo, 15–20 cm; 3 A para la Pi 4, 5 A para la Pi 5",
     "USB-C male pigtail (5 V to the Pi), 90° up/down angle, 15–20 cm; 3 A for a Pi 4, 5 A for a Pi 5"),
    ("1", "Cable micro-HDMI macho acodado 90° a HDMI hembra de panel con 2 tornillos M3, 30 cm (mide su brida: `hdmi_*`)",
     "Angled 90° micro-HDMI male to HDMI female panel-mount cable with 2 M3 screws, 30 cm (measure its flange: `hdmi_*`)"),
]
g.TXT = copy.deepcopy(g.TXT)
g.TXT["es"].update(title="Caja ROS2 rack · Instrucciones de montaje", intro=
    "Segunda caja, tipo rack: la placa de la Pico, la Pi y el convertidor van de pie, en paralelo. 62 × 95 × 145 mm "
    "(0,85 L). La Pi va abajo y el convertidor arriba, para que su calor no suba hacia la Pi. Vale para la Pi 4 y la "
    "Pi 5: solo cambia el marco de la trasera. La OLED, el logo y las bahías de los sensores están en la pared "
    "principal; el XT60 y el interruptor, en la frontal fija; los USB de la Pi y un HDMI de panel, detrás. Se fija al "
    "R2 de pie o tumbada con orejas desmontables. Todo va atornillado a insertos. Antes de imprimir mide lo que indica "
    "el README.")
g.TXT["en"].update(title="ROS2 rack box · Assembly instructions", intro=
    "Second box, rack style: the Pico board, the Pi and the converter stand on edge, side by side. 62 × 95 × 145 mm "
    "(0.85 L). The Pi sits low and the converter high, so its heat does not rise into the Pi. It takes a Pi 4 or a "
    "Pi 5: only the back frame changes. OLED, logo and the sensors' bays are on the main face; XT60 and switch on the "
    "fixed front; the Pi's USB and an HDMI panel jack at the back. It mounts on the R2 standing or lying down, with "
    "removable ears. Every screw goes into an insert. Before printing, measure what the README lists.")
g.BOX_DIMS = (62, 95, 145)
g.WIRING = copy.deepcopy(g.WIRING)
g.WIRING["es"].update(slot="bahías de la cara", back="pared principal", pi="Raspberry Pi 4 / Pi 5",
                      micro="micro-USB recto: sale por la muesca trasera y entra en un USB de la Pi")
g.WIRING["en"].update(slot="face bays", back="main face", pi="Raspberry Pi 4 / Pi 5",
                      micro="straight micro-USB: out of the back notch into a Pi USB port")
g.TXT["es"].update(angled="Conectores: hacia dónde sale cada cable")
g.TXT["en"].update(angled="Plugs: which way each cable goes")

STEPS, bom, fastener_table, write_guide, wiring_svg = g.STEPS, g.bom, g.fastener_table, g.write_guide, g.wiring_svg


def main(images=True):
    g.IMG.mkdir(parents=True, exist_ok=True)
    g.main(images)


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv)
