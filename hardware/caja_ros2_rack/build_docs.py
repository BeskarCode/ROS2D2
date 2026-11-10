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
    ("base.stl", "Base: suelo, trasera, tabique central", "Base: floor, back, central divider"),
    ("tapa.stl", "Tapa (techo + lateral + frontal estrecho)", "Shell (roof + side + narrow front)"),
    ("pulsador.stl", "Varilla del pulsador DISPLAY", "DISPLAY push rod"),
]
g.STEPS = [
    {"n": 1,
     "es": {"title": "Insertos térmicos", "text": "Con el soldador a unos 220 °C mete los 13 insertos rectos y a ras: en la "
            "pared principal, 4 en las columnas, 2 en las pestañas de abajo y 1 en la de arriba; en la base, 2 en lo "
            "alto del tabique, 2 en el tabique para el convertidor y 2 en los bloques del suelo."},
     "en": {"title": "Heat-set inserts", "text": "With the iron at about 220 °C press the 13 inserts in straight and flush: "
            "on the main face, 4 in the columns, 2 in the bottom tabs and 1 in the top tab; on the base, 2 on top of the "
            "divider, 2 in the divider for the converter and 2 in the floor blocks."}},
    {"n": 2,
     "es": {"title": "Convertidor al tabique", "text": "De pie, con la base contra el tabique, las aletas hacia fuera y los "
            "cables hacia delante. Comprueba antes con el calibre sus agujeros (`conv_holes`)."},
     "en": {"title": "Converter onto the divider", "text": "On edge, its base plate against the divider, fins outwards, "
            "wires to the front. Check its holes (`conv_holes`) with a caliper first."}},
    {"n": 3,
     "es": {"title": "Raspberry Pi al tabique", "text": "Sobre sus 4 columnas, con los USB y el Ethernet a ras de la trasera "
            "y el USB-C abajo. Conecta el USB-C acodado y empálmalo con la salida de 5 V del convertidor."},
     "en": {"title": "Raspberry Pi onto the divider", "text": "On its 4 standoffs, USB and Ethernet flush with the back, "
            "USB-C at the bottom. Plug in the angled USB-C and join it to the converter's 5 V output."}},
    {"n": 4,
     "es": {"title": "XT60 e interruptor en la pared principal", "text": "Desde fuera, abajo: el XT60E-F girado, con 2 "
            "tornillos y sus tuercas por dentro, y el interruptor a presión."},
     "en": {"title": "XT60 and switch on the main face", "text": "From outside, low down: the XT60E-F turned on its side "
            "with 2 screws and their nuts inside, and the switch snapped in."}},
    {"n": 5,
     "es": {"title": "Varilla y placa de la Pico", "text": "Mete la varilla desde dentro por su guía y atornilla la placa a "
            "las 4 columnas, componentes hacia la pared. Aprieta los 5 V en el borne J1, pincha el micro-USB acodado en "
            "la Pico y conecta los sensores: sus cables salen por la ranura de arriba."},
     "en": {"title": "Push rod and Pico board", "text": "Slide the rod into its guide from inside and screw the board onto "
            "the 4 columns, parts towards the wall. Tighten the 5 V in terminal J1, plug the angled micro-USB into the "
            "Pico and connect the sensors: their cables leave through the slot at the top."}},
    {"n": 6,
     "es": {"title": "Pared principal a la base", "text": "Pasa los cables de 24 V (XT60 → interruptor → convertidor) y los "
            "5 V del borne J1 por el hueco de abajo del tabique. Atornilla la pared desde debajo del suelo."},
     "en": {"title": "Main face onto the base", "text": "Run the 24 V wires (XT60 → switch → converter) and the 5 V to "
            "terminal J1 through the gap at the bottom of the divider. Screw the face on from under the floor."}},
    {"n": 7,
     "es": {"title": "Tapa", "text": "Bájala desde arriba y pon los 3 tornillos del techo y los 2 del lateral."},
     "en": {"title": "Shell", "text": "Lower it from above and fit the 3 roof screws and the 2 side screws."}},
    {"n": 8,
     "es": {"title": "USB y fijación al R2", "text": "Saca el micro-USB por la muesca de la trasera y enchúfalo en un USB de "
            "la Pi. Atornilla la caja al R2 por sus 4 orejetas."},
     "en": {"title": "USB and onto the R2", "text": "Bring the micro-USB out of the notch in the back into a Pi USB port. "
            "Screw the box to the R2 through its 4 ears."}},
]
g.TXT = copy.deepcopy(g.TXT)
g.TXT["es"].update(title="Caja ROS2 rack · Instrucciones de montaje", intro=
    "Segunda caja, tipo rack: la placa de la Pico, la Pi y el convertidor van de pie, en paralelo. 78 × 95 × 127 mm "
    "(0,94 L, casi la mitad que la mini torre). La OLED, el logo, el interruptor y el XT60 están en la pared principal; "
    "los USB de la Pi, detrás. Antes de imprimir mide lo que indica el README.")
g.TXT["en"].update(title="ROS2 rack box · Assembly instructions", intro=
    "Second box, rack style: the Pico board, the Pi and the converter stand on edge, side by side. 78 × 95 × 127 mm "
    "(0.94 L, about half the mini tower). OLED, logo, switch and XT60 are on the main face; the Pi's USB at the back. "
    "Before printing, measure what the README lists.")
g.WIRING = copy.deepcopy(g.WIRING)
g.WIRING["es"].update(slot="ranura lateral", back="pared principal",
                      micro="micro-USB acodado: sale por la muesca trasera y entra en un USB de la Pi")
g.WIRING["en"].update(slot="side slot", back="main face",
                      micro="angled micro-USB: out of the back notch into a Pi USB port")

STEPS, bom, fastener_table, write_guide, wiring_svg = g.STEPS, g.bom, g.fastener_table, g.write_guide, g.wiring_svg


def main(images=True):
    g.IMG.mkdir(parents=True, exist_ok=True)
    for lang in ("es", "en"):           # same angled plugs as the first box
        shutil.copy(HERE.parent / "caja_ros2" / "montaje" / "img" / f"conectores_{lang}.svg", g.IMG / f"conectores_{lang}.svg")
    g.main(images)


if __name__ == "__main__":
    main(images="--no-images" not in sys.argv)
