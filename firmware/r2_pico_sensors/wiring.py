# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Generate firmware/r2_pico_sensors/wiring.svg (Pico 2 + 4 VL53L0X + 3 HC-SR04)."""
import sys

OUT = sys.argv[1]
W, H = 1760, 1040
C = dict(v3="#d62828", v5="#f77f00", gnd="#222", sda="#1d6fd8", scl="#2a9d3a",
         xs="#8e44ad", trig="#c9a000", echo="#0b8a8a", board="#1f6f43", txt="#111", mute="#666")
o = []
add = o.append


def text(x, y, s, size=13, anchor="start", color=None, weight="normal"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color or C["txt"]}" font-weight="{weight}">{s}</text>')


def line(pts, color, w=3):
    d = " ".join(f"{x},{y}" for x, y in pts)
    add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"/>')


def dot(x, y, color):
    add(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')


def tag(x, y, s, color, anchor="start"):
    w = 7.3 * len(s) + 14
    x0 = x if anchor == "start" else x - w
    add(f'<rect x="{x0}" y="{y-12}" width="{w}" height="22" rx="4" fill="#fff" stroke="{color}" stroke-width="2"/>')
    text(x0 + 7, y + 4, s, 12.5, color=color, weight="bold")


# --- Pico 2, top view, USB at the top ---------------------------------------------
PX0, PX1, PY0 = 330, 600, 200
pitch = 31
left = ["GP0", "GP1", "GND", "GP2", "GP3", "GP4", "GP5", "GND", "GP6", "GP7", "GP8", "GP9", "GND",
        "GP10", "GP11", "GP12", "GP13", "GND", "GP14", "GP15"]                      # pins 1..20
right = {21: "GP16", 22: "GP17", 23: "GND", 24: "GP18", 25: "GP19", 26: "GP20", 27: "GP21", 28: "GND",
         29: "GP22", 30: "RUN", 31: "GP26", 32: "GP27", 33: "GND", 34: "GP28", 35: "ADC_VREF",
         36: "3V3(OUT)", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS"}


def ly(n):            # left pin n (1..20), top to bottom
    return PY0 + 30 + (n - 1) * pitch


def ry(n):            # right pin n (21..40): 40 at the top, 21 at the bottom
    return PY0 + 30 + (40 - n) * pitch


PY1 = ly(20) + 30
add(f'<rect x="{PX0}" y="{PY0}" width="{PX1-PX0}" height="{PY1-PY0}" rx="10" fill="{C["board"]}"/>')
add(f'<rect x="{(PX0+PX1)/2-30}" y="{PY0-18}" width="60" height="30" rx="4" fill="#bbb" stroke="#777"/>')
text((PX0 + PX1) / 2, PY0 - 24, "USB → Pi 4", 12, "middle", C["mute"])
text((PX0 + PX1) / 2, (PY0 + PY1) / 2 - 10, "Raspberry Pi", 15, "middle", "#fff", "bold")
text((PX0 + PX1) / 2, (PY0 + PY1) / 2 + 10, "Pico 2", 15, "middle", "#fff", "bold")
text((PX0 + PX1) / 2, (PY0 + PY1) / 2 + 30, "(vista desde arriba)", 11, "middle", "#cfe")
add(f'<circle cx="{(PX0+PX1)/2}" cy="{PY0+40}" r="6" fill="#7f7" stroke="#fff"/>')
text((PX0 + PX1) / 2, PY0 + 62, "LED GP25", 10, "middle", "#cfe")
used = {}
for i, name in enumerate(left, 1):
    y = ly(i)
    add(f'<circle cx="{PX0+10}" cy="{y}" r="6" fill="#e9c46a" stroke="#555"/>')
    text(PX0 + 22, y + 4, f"{i} · {name}", 11, color="#fff")
for n, name in right.items():
    y = ry(n)
    add(f'<circle cx="{PX1-10}" cy="{y}" r="6" fill="#e9c46a" stroke="#555"/>')
    text(PX1 - 22, y + 4, f"{name} · {n}", 11, "end", "#fff")

# --- rails ------------------------------------------------------------------------
RAIL = dict(v3=(36, 70, 615, "3,3 V"), gnd=(38, 92, 630, "GND"), sda=(21, 114, 645, "SDA · GP16"),
            scl=(22, 136, 660, "SCL · GP17"))
for k, (pin, y, rx, label) in RAIL.items():
    line([(PX1 - 10, ry(pin)), (rx, ry(pin)), (rx, y), (W - 30, y)], C[k])
    text(W - 30, y - 5, label, 12, "end", C[k], "bold")
RAIL5 = dict(v5=(40, 548, 505, "5 V · VBUS"), gnd=(38, 570, 460, "GND"))
line([(PX1 - 10, ry(40)), (675, ry(40)), (675, 548), (W - 30, 548)], C["v5"])
text(W - 30, 543, "5 V · VBUS", 12, "end", C["v5"], "bold")
line([(630, 92), (630, 570), (W - 30, 570)], C["gnd"])
dot(630, 92, C["gnd"])
text(W - 30, 590, "GND", 12, "end", C["gnd"], "bold")

# --- VL53L0X ----------------------------------------------------------------------
TOF = [("tof_front_left", 2, 4), ("tof_front", 3, 5), ("tof_front_right", 4, 6), ("tof_floor", 5, 7)]
for j, (name, gp, pin) in enumerate(TOF):
    x, y = 730 + j * 250, 215
    add(f'<rect x="{x}" y="{y}" width="215" height="120" rx="8" fill="#f3e8fb" stroke="{C["xs"]}" stroke-width="2"/>')
    text(x + 107, y + 62, "VL53L0X", 15, "middle", C["xs"], "bold")
    text(x + 107, y + 82, name, 12, "middle")
    pins = [("VIN", "v3", 70), ("GND", "gnd", 92), ("SCL", "scl", 136), ("SDA", "sda", 114), ("GPIO1", None, 0)]
    for k, (pn, net, ryy) in enumerate(pins):
        px = x + 22 + k * 34
        text(px, y + 22, pn, 9.5, "middle", C["mute"])
        if net:
            line([(px, ryy), (px, y)], C[net], 2.5)
            dot(px, ryy, C[net])
        else:
            text(px, y + 36, "(libre)", 9, "middle", C["mute"])
    px = x + 195
    text(px, y + 22, "XSHUT", 9.5, "middle", C["mute"])
    line([(px, y + 120), (px, y + 150)], C["xs"], 2.5)
    tag(px, y + 162, f"XSHUT → GP{gp} (pin {pin})", C["xs"], "end")
    used[pin] = (f"{name} XSHUT", C["xs"])

# --- HC-SR04 ----------------------------------------------------------------------
SON = [("sonar_front_left", 10, 14, 11, 15), ("sonar_front_right", 12, 16, 13, 17),
       ("sonar_rear", 14, 19, 15, 20)]
for j, (name, tg, tp, eg, ep) in enumerate(SON):
    x, y = 730 + j * 330, 620
    add(f'<rect x="{x}" y="{y}" width="250" height="110" rx="8" fill="#fff6dc" stroke="{C["trig"]}" stroke-width="2"/>')
    text(x + 125, y + 50, "HC-SR04", 15, "middle", "#8a6d00", "bold")
    text(x + 125, y + 70, name, 12, "middle")
    for px, pn, net, ryy in ((x + 30, "VCC", "v5", 548), (x + 220, "GND", "gnd", 570)):
        text(px, y + 20, pn, 9.5, "middle", C["mute"])
        line([(px, ryy), (px, y)], C[net], 2.5)
        dot(px, ryy, C[net])
    # TRIG straight to its pin
    px = x + 70
    text(px, y + 100, "TRIG", 9.5, "middle", C["mute"])
    line([(px, y + 110), (px, y + 140)], C["trig"], 2.5)
    tag(px - 50, y + 152, f"TRIG → GP{tg} (pin {tp})", "#8a6d00")
    # ECHO through the divider: 1k to the pin node, 2k from the node to GND
    ex = x + 170
    text(ex, y + 100, "ECHO", 9.5, "middle", C["mute"])
    line([(ex, y + 110), (ex, y + 130)], C["echo"], 2.5)
    add(f'<rect x="{ex-8}" y="{y+130}" width="16" height="40" fill="#fff" stroke="{C["echo"]}" stroke-width="2"/>')
    text(ex + 14, y + 155, "1 kΩ", 11, color=C["echo"], weight="bold")
    line([(ex, y + 170), (ex, y + 195)], C["echo"], 2.5)
    dot(ex, y + 195, C["echo"])
    line([(ex, y + 195), (ex + 40, y + 195)], C["echo"], 2.5)
    tag(ex + 40, y + 196, f"→ GP{eg} (pin {ep})", C["echo"])
    line([(ex, y + 195), (ex, y + 215)], C["gnd"], 2.5)
    add(f'<rect x="{ex-8}" y="{y+215}" width="16" height="40" fill="#fff" stroke="{C["gnd"]}" stroke-width="2"/>')
    text(ex - 14, y + 240, "2 kΩ", 11, "end", weight="bold")
    line([(ex, y + 255), (ex, y + 270)], C["gnd"], 2.5)
    line([(ex - 12, y + 270), (ex + 12, y + 270)], C["gnd"], 3)
    line([(ex - 7, y + 276), (ex + 7, y + 276)], C["gnd"], 3)
    text(ex + 16, y + 275, "GND", 10, color=C["mute"])
    used[tp] = (f"{name} TRIG", "#8a6d00")
    used[ep] = (f"{name} ECHO (por divisor)", C["echo"])

# --- tags on the Pico's left pins --------------------------------------------------
for pin, (label, color) in used.items():
    y = ly(pin)
    line([(PX0 + 4, y), (PX0 - 20, y)], color, 3)
    tag(PX0 - 24, y + 1, label, color, "end")

# --- title, warning, notes ---------------------------------------------------------
text(30, 40, "ROS2D2 · conexión de los sensores de distancia a la Pico 2", 22, weight="bold")
text(30, 64, "Pines de sensors.yaml (Setup → Sensors). Si cambias un pin allí, cambia el cable: no hay que reflashear.", 13, color=C["mute"])
add(f'<rect x="30" y="905" width="560" height="110" rx="8" fill="#fde8e8" stroke="{C["v3"]}" stroke-width="3"/>')
text(46, 932, "⚠ ECHO del HC-SR04 sale a 5 V", 16, color=C["v3"], weight="bold")
text(46, 956, "La Pico solo aguanta 3,3 V: sin el divisor 1 kΩ / 2 kΩ", 13)
text(46, 976, "(o un conversor de nivel) se estropea el pin.", 13)
text(46, 998, "ECHO → 1 kΩ → pin de la Pico, y de ese pin → 2 kΩ → GND (≈ 3,3 V).", 13)
notes = ["VL53L0X a 3,3 V (pin 36). HC-SR04 a 5 V (VBUS, pin 40: solo con la Pico por USB, como va).",
         "Todos los VL53L0X comparten SDA/SCL (GP16 / GP17). Cable I2C corto: menos de 50 cm.",
         "Cada VL53L0X tiene su XSHUT: con él la Pico les da direcciones distintas al arrancar.",
         "TRIG va directo (3,3 V basta para dispararlo). GPIO1 del VL53L0X no se usa.",
         "Consumo: ~20 mA por VL53L0X y ~15 mA por HC-SR04: los 7 caben en el USB de la Pi.",
         "Reservados en la Pico: GP16, GP17 (I2C), GP23, GP24, GP25 (LED) — no ponerles sensores."]
for i, n in enumerate(notes):
    text(620, 925 + i * 18, "· " + n, 12.5)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Segoe UI, Helvetica, Arial, sans-serif">'
       f'<rect width="{W}" height="{H}" fill="#fff"/>' + "".join(o) + "</svg>\n")
open(OUT, "w", encoding="utf-8").write(svg)
print("ok", OUT)
