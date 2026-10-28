"""Write r2_pico_carrier.kicad_sch from parts.py: each part's symbol (copied from KiCad's own
libraries), a net label on every connected pin and a no-connect flag on every free one.
Blocks by function, so the PDF reads like a hand-drawn schematic.

    $KPY hardware/r2_pico_carrier/gen/make_sch.py
"""
import os
import re
import uuid

from parts import PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "r2_pico_carrier.kicad_sch")
SYMBOLS = os.environ.get(
    "KICAD_SYM", r"C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\share\kicad\symbols")
NS = uuid.UUID("6f1d0c3e-2b7a-4c51-9a55-7d2f4c0e9b10")
ROOT = str(uuid.uuid5(NS, "root"))
FONT = "(effects (font (size 1.27 1.27)))"
HIDDEN = "(effects (font (size 1.27 1.27)) (hide yes))"


def uid(*key):
    return str(uuid.uuid5(NS, "/".join(map(str, key))))


def block(text, start):
    """The balanced (...) expression starting at text[start]."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced")


_libs = {}


def lib_symbol(lib_id):
    """(symbol "Lib:Name" ...) for lib_symbols, and its pins {number: (x, y, angle)}."""
    lib, name = lib_id.split(":")
    if lib not in _libs:
        with open(os.path.join(SYMBOLS, f"{lib}.kicad_sym"), encoding="utf-8") as f:
            _libs[lib] = f.read()
    text = _libs[lib]
    m = re.search(r'\(symbol "%s"' % re.escape(name), text)
    body = block(text, m.start())
    if "(extends " in body:
        raise ValueError(f"{lib_id} extends another symbol: pick the base one")
    pins = {}
    for pm in re.finditer(r"\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)", body):
        pb = block(body, pm.start())
        num = re.search(r'\(number "([^"]*)"', pb).group(1)
        pins[num] = (float(pm.group(1)), float(pm.group(2)), int(pm.group(3)))
    return body.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1), pins


# Where each part goes (mm, A3 sheet). Blocks: power, Pico, I2C, VL, US, LEDs, display.
def placement():
    at = {}
    x = 30
    for ref in ("J1", "D1", "J5", "R6", "R7", "D5", "F1", "C1", "C2", "D2", "C4", "D4", "R1"):
        at[ref] = (x, 40)
        x += 16
    at["JP1"], at["JP2"] = (40, 125), (95, 125)
    for i, ref in enumerate(("R2", "R3", "U1", "C5", "R4", "R5")):
        at[ref] = (225 + i * 28, 45)
    for n in range(1, 5):
        at[f"VL{n}"] = (165 + (n - 1) * 60, 100)
    for n in range(1, 6):
        x0 = 165 + (n - 1) * 48
        at[f"US{n}"], at[f"R{10 + n}"], at[f"R{20 + n}"] = (x0, 150), (x0 + 22, 145), (x0 + 22, 170)
    for k in range(1, 10):
        at[f"R{30 + k}"] = (160 + (k - 1) * 27, 215)
        at[f"LED{k}"] = (160 + (k - 1) * 27, 240)
    at["J2"], at["SW1"] = (40, 230), (85, 230)
    at["J3"], at["J4"] = (40, 255), (85, 255)
    for k in range(1, 9):
        at[f"H{k}"] = (150 + (k - 1) * 12, 270)
    g = 1.27                                       # KiCad's connection grid
    return {r: (round(x / g) * g, round(y / g) * g) for r, (x, y) in at.items()}


def label(net, x, y, angle, key):
    # global labels: the net is called "SDA" on the board too, not "/SDA"
    just = {0: "left", 90: "left", 180: "right", 270: "right"}[angle]
    return (f'(global_label "{net}" (shape passive) (at {x:.2f} {y:.2f} {angle}) (fields_autoplaced yes) '
            f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid("label", *key)}"))')


def main():
    at = placement()
    missing = set(PARTS) - set(at)
    if missing:
        raise SystemExit(f"no place for {sorted(missing)}")
    lib_blocks, out = {}, []
    flags = {"+3V3", "GND", "+5V", "VSYS", "5V_IN", "VBUS_C"}      # PWR_FLAG: these nets are fed
    for ref, part in PARTS.items():
        body, pins = lib_symbol(part.symbol)
        lib_blocks[part.symbol] = body
        x, y = at[ref]
        props = [("Reference", ref, False), ("Value", part.value, False),
                 ("Footprint", part.footprint, True), ("Datasheet", "", True), ("LCSC", part.lcsc, True)]
        text = [f'(symbol (lib_id "{part.symbol}") (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) '
                f'(in_bom {"no" if ref.startswith("H") else "yes"}) (on_board yes) (dnp no) '
                f'(uuid "{uid("sym", ref)}")']
        for i, (k, v, hide) in enumerate(props):
            text.append(f'(property "{k}" "{v}" (at {x + 3} {y - 4 + i * 2.5} 0) {HIDDEN if hide else FONT})')
        for num in pins:
            text.append(f'(pin "{num}" (uuid "{uid("pin", ref, num)}"))')
        text.append(f'(instances (project "r2_pico_carrier" (path "/{ROOT}" (reference "{ref}") (unit 1)))))')
        out.append(" ".join(text))
        for num, (px, py, ang) in pins.items():
            sx, sy = x + px, y - py
            net = part.pads.get(num, "")
            if net:
                out.append(label(net, sx, sy, (ang + 180) % 360, (ref, num)))
            else:
                out.append(f'(no_connect (at {sx:.2f} {sy:.2f}) (uuid "{uid("nc", ref, num)}"))')
    body, pins = lib_symbol("power:PWR_FLAG")
    lib_blocks["power:PWR_FLAG"] = body
    for i, net in enumerate(sorted(flags)):
        x, y = round((30 + i * 20) / 1.27) * 1.27, round(275 / 1.27) * 1.27
        out.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) '
                   f'(in_bom no) (on_board no) (dnp no) (uuid "{uid("flag", net)}") '
                   f'(property "Reference" "#FLG0{i + 1}" (at {x} {y - 4} 0) {HIDDEN}) '
                   f'(property "Value" "PWR_FLAG" (at {x} {y - 6} 0) {FONT}) '
                   f'(property "Footprint" "" (at {x} {y} 0) {HIDDEN}) (property "Datasheet" "" (at {x} {y} 0) {HIDDEN}) '
                   f'(pin "1" (uuid "{uid("flagpin", net)}")) '
                   f'(instances (project "r2_pico_carrier" (path "/{ROOT}" (reference "#FLG0{i + 1}") (unit 1)))))')
        out.append(label(net, x, y, 270, ("flag", net)))
    titles = [("R2 Pico carrier — power", 25, 25), ("Pico 2 (plugs in, pins down)", 25, 95),
              ("I2C: Pico bus (display, Qwiic, EXP); U1 repeater to VL1-VL4 (cables up to 1 m)", 160, 25),
              ("VL53L0X connectors (GY-530 order)", 160, 85),
              ("HC-SR04 connectors, ECHO 1k/2k dividers", 160, 135),
              ("Status LEDs, one GPIO each (LED1-4 = VL1-4, LED5-9 = US1-5)", 140, 200), ("Display, button, expansion (Qwiic, header)", 25, 210)]
    for t, x, y in titles:
        out.append(f'(text "{t}" (exclude_from_sim no) (at {x} {y} 0) (effects (font (size 2 2) bold) (justify left)) '
                   f'(uuid "{uid("text", t)}"))')
    doc = ("(kicad_sch (version 20250114) (generator \"r2_pico_carrier_gen\") (generator_version \"10.0\") "
           f'(uuid "{ROOT}") (paper "A3") '
           '(title_block (title "R2 Pico carrier") (date "2026-10-27") (rev "A") '
           '(company "ROS2D2 · Astromech Spain") (comment 1 "Generated by gen/make_sch.py from gen/parts.py"))\n'
           "(lib_symbols\n" + "\n".join(lib_blocks.values()) + "\n)\n" + "\n".join(out) +
           f'\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no)\n)\n')
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    pro = os.path.join(HERE, "..", "r2_pico_carrier.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            f.write('{\n  "meta": {\n    "filename": "r2_pico_carrier.kicad_pro",\n    "version": 1\n  }\n}\n')
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
