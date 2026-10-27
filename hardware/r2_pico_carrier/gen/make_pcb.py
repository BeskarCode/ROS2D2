"""Write r2_pico_carrier.kicad_pcb from parts.py: outline, M3 holes, every footprint placed
with its nets, silkscreen (connector names and pins, the Pico's outline, the branding on the
back) and the GND pour. No tracks: route.py routes it.

    $KPY hardware/r2_pico_carrier/gen/make_pcb.py

Layout (top view, mm, origin at the top-left corner):
  - the Pico in the middle, its USB on the top edge (the cable from the Pi plugs in there);
  - HC-SR04 connectors US1-US5 on the left (their GPIOs are on the Pico's left row), each
    with its ECHO divider and its LED;
  - VL53L0X connectors VL1-VL4 on the right (next to the I2C pins), VL3-VL4 marked > 50 cm;
  - the 5 V input and its protection bottom left; display socket and button bottom right.
"""
import os

import pcbnew
from PIL import Image

from parts import PARTS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "r2_pico_carrier.kicad_pcb")
FP = os.environ.get("KICAD_FP", r"C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints")
CLI = os.environ.get("KICAD_CLI", r"C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe")
# Astromech Spain's round logo (astromechspain.com, AstromechSpain_logo_circular_b.png, 1000 px)
LOGO = os.path.join(HERE, "astromech-spain-logo-circular.png")
# The OLED module (0.96" SSD1306/SSD1315, 27.3 x 27.8 mm; pins centred 2 mm from its top edge;
# holes 23.5 x 23.8 mm apart) plugs into J2's socket lying flat, on M2 standoffs in H5-H8
OLED_X, OLED_TOP, OLED_W, OLED_H = 58.5, 60.0, 27.3, 27.8

W, H = 80.0, 90.0                     # board size
PICO_X, PICO_TOP = 40.0, 2.0          # Pico centre line and top edge (USB end)
ROW = 8.89                            # Pico pin rows at +-8.89 mm from its centre
PIN1_Y = PICO_TOP + 1.37 + 0.0        # first pin, 1.37 mm under the Pico's top edge
POWER_NETS = ("5V_IN", "5V_FUSED", "+5V", "VSYS", "VLED", "+3V3", "GND")

mm = pcbnew.FromMM


def at(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


US_Y = [12 + i * 10 for i in range(5)]
VL_Y = [12, 24, 39, 51]
US_PINS = ["5V", "TR", "EC", "G"]
VL_PINS = ["3V3", "G", "SCL", "SDA", "-", "XS"]
HEADER_ROT = 90                       # pin 1 on the left, the rest to its right


# ref -> (x, y, rotation degrees)
def placement():
    p = {"JP1": (PICO_X - ROW, PIN1_Y, 0), "JP2": (PICO_X + ROW, PIN1_Y, 0)}
    for i, y in enumerate(US_Y):                          # US1..US5
        p[f"US{i + 1}"] = (3.0, y, HEADER_ROT)
        p[f"R{11 + i}"] = (15.0, y - 1.2, 0)              # 1k
        p[f"R{21 + i}"] = (15.0, y + 1.6, 0)              # 2k
        p[f"LED{5 + i}"] = (21.0, y, 0)
        p[f"C{15 + i}"] = (26.5, y, 90)
    for i, y in enumerate(VL_Y):                          # VL1..VL4
        p[f"VL{i + 1}"] = (55.0, y, HEADER_ROT)
        p[f"LED{1 + i}"] = (72.6, y, 90)       # pads above and below: clear of the header
        p[f"C{11 + i}"] = (78.3, y, 90)
    p.update({"R2": (57.0, 7.0, 0), "R3": (61.0, 7.0, 0), "C4": (52.5, 6.0, 90),
              "R6": (52.5, 35.5, 90), "C5": (57.0, 33.0, 90), "U1": (62.0, 33.0, 0),
              "R4": (68.0, 31.5, 0), "R5": (68.0, 34.5, 0),
              "J1": (10.5, 63.0, 0), "F1": (21.5, 59.5, 0), "D1": (28.0, 59.5, 180),
              "C1": (21.5, 64.5, 0), "C2": (25.0, 64.5, 0),
              "D2": (35.0, 59.5, 180), "D3": (35.0, 64.5, 180), "C3": (39.5, 64.5, 90),
              "D4": (40.8, 59.5, 0), "R1": (44.0, 57.0, 0),
              "J2": (OLED_X - 3.81, OLED_TOP + 2.0, HEADER_ROT), "SW1": (38.0, 79.0, 0)})
    for k, (dx, dy) in enumerate(((1.9, 2.0), (OLED_W - 1.9, 2.0), (1.9, OLED_H - 2.0), (OLED_W - 1.9, OLED_H - 2.0)), 5):
        p[f"H{k}"] = (OLED_X - OLED_W / 2 + dx, OLED_TOP + dy, 0)
    for k, (x, y) in enumerate(((3.5, 3.5), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)), 1):   # M3
        p[f"H{k}"] = (x, y, 0)
    return p


def check(board):
    """Every pad on the board (0.5 mm in from the edge) and pin 1 of each header on the left."""
    bad = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        pads = {p.GetNumber(): p.GetPosition() for p in fp.Pads()}
        for num, pos in pads.items():
            x, y = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (0.5 <= x <= W - 0.5 and 0.5 <= y <= H - 0.5) and num:
                bad.append(f"{ref} pad {num} at ({x:.1f}, {y:.1f}) is off the board")
        if ref.startswith(("US", "VL")) or ref == "J2":
            xs = [pcbnew.ToMM(pads[str(k)].x) for k in range(1, len(pads) + 1)]
            if xs != sorted(xs):
                bad.append(f"{ref}: pin 1 is not on the left")
    if bad:
        raise SystemExit("\n".join(bad))


def text(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, bold=False, angle=0, justify=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(at(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(max(0.15, size * (0.2 if bold else 0.15))))
    t.SetTextAngleDegrees(angle)
    if justify:
        t.SetHorizJustify(justify)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def line(board, x0, y0, x1, y1, layer=pcbnew.F_SilkS, width=0.15):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(at(x0, y0))
    s.SetEnd(at(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def rect(board, x0, y0, x1, y1, layer, width=0.15, filled=False):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(at(x0, y0))
    s.SetEnd(at(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(mm(width) if not filled else 0)
    s.SetFilled(filled)
    board.Add(s)


def logo(board, cx, y0, width, layer):
    """The Astromech Spain logo as silkscreen: its black and red parts are printed, the yellow
    stripe of the flag is left out so the flag still reads. Drawn at 0.05 mm per pixel from a
    resampled mask (smooth edges), as filled rectangles: one per run of pixels, rows with the
    same runs merged. On the back it is mirrored, so it reads right when the board is turned over."""
    src = Image.open(LOGO).convert("RGBA")
    mask = Image.new("L", src.size, 0)
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = src.getpixel((x, y))
            yellow = r > 180 and g > 150 and b < 100
            mask.putpixel((x, y), a if not yellow else 0)
    px = 0.05
    cols = int(width / px)
    mask = mask.resize((cols, round(src.height * cols / src.width)), Image.LANCZOS)
    back = layer == pcbnew.B_SilkS

    def runs(y):
        out, x = [], 0
        while x < cols:
            if mask.getpixel((x, y)) >= 128:
                x1 = x
                while x1 < cols and mask.getpixel((x1, y)) >= 128:
                    x1 += 1
                out.append((x, x1))
                x = x1
            else:
                x += 1
        return out

    y, n = 0, 0
    while y < mask.height:
        r = runs(y)
        y1 = y + 1
        while y1 < mask.height and runs(y1) == r:
            y1 += 1
        for xa, xb in r:
            a, b = cx - width / 2 + xa * px, cx - width / 2 + xb * px
            if back:
                a, b = 2 * cx - b, 2 * cx - a
            rect(board, a, y0 + y * px, b, y0 + y1 * px, layer, filled=True)
            n += 1
        y = y1
    return y0 + mask.height * px


def silkscreen(board):
    # The Pico, as seen plugged in: outline, USB, pin 1, "pins down"
    rect(board, PICO_X - 11.2, PICO_TOP - 0.3, PICO_X + 11.2, PICO_TOP + 51.3, pcbnew.F_SilkS)
    text(board, "USB", PICO_X, PICO_TOP + 2.2, 1.0, bold=True)
    text(board, "PICO 2", PICO_X, PICO_TOP + 24, 1.5, bold=True)
    text(board, "pins down", PICO_X, PICO_TOP + 26.5, 0.9)
    text(board, "1", PICO_X - ROW - 1.8, PIN1_Y, 0.9, bold=True)
    for i, y in enumerate(US_Y):
        text(board, f"US{i + 1}", 3.0 - 1.3, y - 2.9, 1.0, bold=True, justify=pcbnew.GR_TEXT_H_ALIGN_LEFT)
        for k, name in enumerate(US_PINS):
            text(board, name, 3.0 + k * 2.54, y + 2.75, 0.8)
    for i, y in enumerate(VL_Y):
        text(board, f"VL{i + 1}", 55.0 - 1.3, y - 2.9, 1.0, bold=True, justify=pcbnew.GR_TEXT_H_ALIGN_LEFT)
        for k, name in enumerate(VL_PINS):
            text(board, name, 55.0 + k * 2.54, y + 2.75, 0.8)
    text(board, "< 50 cm", 66.0, 9.6, 0.9, bold=True)
    text(board, "> 50 cm", 66.0, 36.6, 0.9, bold=True)
    line(board, 54.0, 29.0, W - 0.5, 29.0)
    text(board, "+5V  GND", 13.0, 56.6, 0.8, bold=True)
    # the OLED, lying flat: its outline, its pins, what goes there
    x0 = OLED_X - OLED_W / 2
    rect(board, x0, OLED_TOP, x0 + OLED_W, OLED_TOP + OLED_H, pcbnew.F_SilkS)
    for k, name in enumerate(["G", "V", "SCL", "SDA"]):
        text(board, name, OLED_X - 3.81 + k * 2.54, OLED_TOP - 1.3, 0.8)
    text(board, "OLED 0.96in SSD1306 I2C", OLED_X, OLED_TOP + 12.0, 1.0, bold=True)
    text(board, "screen up, M2 standoffs 11 mm", OLED_X, OLED_TOP + 14.5, 0.8)
    text(board, "GND VCC SCL SDA", OLED_X, OLED_TOP + 16.7, 0.8)
    text(board, "DISPLAY", 38.0, 83.5, 0.8, bold=True)
    text(board, "ROS2D2 · NandoMadrid · rev A", 22.0, 88.3, 0.8, bold=True)
    # Back: the branding, where there are no pads: "ROS2D2" between the Pico's rows,
    # the logo and the rest along the bottom strip
    text(board, "ROS2D2", PICO_X, 27.0, 5.0, pcbnew.B_SilkS, bold=True, angle=90)
    logo(board, 35.0, 59.0, 30.0, pcbnew.B_SilkS)
    text(board, "ROS2D2", 63.0, 69.0, 2.0, pcbnew.B_SilkS, bold=True)
    text(board, "by NandoMadrid", 63.0, 72.5, 1.4, pcbnew.B_SilkS, bold=True)
    text(board, "www.astromechspain.com", 63.0, 76.0, 1.2, pcbnew.B_SilkS)
    text(board, "R2 Pico carrier · rev A", 63.0, 79.0, 1.0, pcbnew.B_SilkS)


def rules(board):
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(at(0, H))             # placement files: origin at the bottom-left corner
    ds.m_TrackMinWidth = mm(0.127)        # 5 mil: standard at JLCPCB and PCBWay
    ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)
    ncs = ds.m_NetSettings
    default = ncs.GetDefaultNetclass()
    default.SetTrackWidth(mm(0.25))
    default.SetClearance(mm(0.15))       # U1's 0.65 mm pitch pads are 0.15 mm apart
    default.SetViaDiameter(mm(0.6))
    default.SetViaDrill(mm(0.3))
    power = pcbnew.NETCLASS("Power")
    power.SetTrackWidth(mm(0.5))
    power.SetClearance(mm(0.15))
    power.SetViaDiameter(mm(0.8))
    power.SetViaDrill(mm(0.4))
    ncs.SetNetclass("Power", power)
    for net in POWER_NETS:
        ncs.SetNetclassPatternAssignment(net, "Power")


def schematic_free_pins():
    """{(ref, pad): "unconnected-(...)"}: the pins the schematic leaves free get the same
    net on the board, so they agree pad by pad (DRC schematic parity)."""
    import subprocess
    import tempfile
    import xml.etree.ElementTree as ET
    out = os.path.join(tempfile.mkdtemp(), "net.xml")
    sch = os.path.join(HERE, "..", "r2_pico_carrier.kicad_sch")
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, sch],
                   check=True, capture_output=True)
    free = {}
    for net in ET.parse(out).getroot().iter("net"):
        if net.get("name").startswith("unconnected-"):
            for node in net.iter("node"):
                free[(node.get("ref"), node.get("pin"))] = net.get("name")
    return free


def main():
    board = pcbnew.BOARD()
    rules(board)
    nets = {}
    free = schematic_free_pins()
    for name in sorted(set(free.values())):
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    for part in PARTS.values():
        for n in part.pads.values():
            if n and n not in nets:
                nets[n] = pcbnew.NETINFO_ITEM(board, n)
                board.Add(nets[n])
    place = placement()
    for ref, part in PARTS.items():
        lib, name = part.footprint.split(":")
        fp = pcbnew.FootprintLoad(os.path.join(FP, f"{lib}.pretty"), name)
        fp.SetReference(ref)
        fp.SetValue(part.value)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        fp.Reference().SetTextThickness(mm(0.15))
        fp.SetField("LCSC", part.lcsc)
        fp.GetField("LCSC").SetVisible(False)        # for the BOM, never on the silkscreen
        # only the parts a person plugs into keep their name on the silkscreen
        fp.Reference().SetVisible(ref in ("J2", "SW1", "U1"))
        fp.SetFPIDAsString(part.footprint)
        x, y, rot = place[ref]
        fp.SetPosition(at(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            net = part.pads.get(pad.GetNumber(), "") or free.get((ref, pad.GetNumber()), "")
            if net:
                pad.SetNet(nets[net])
        board.Add(fp)
    check(board)
    rect(board, 0, 0, W, H, pcbnew.Edge_Cuts, 0.1)
    silkscreen(board)
    # GND pour on the back only: the router then takes every GND pad down to it with a via
    # (with a front pour too it took pads as joined through islands that were not)
    for layer in (pcbnew.B_Cu,):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets["GND"])
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # thermal spokes got blocked by back tracks
        o = z.Outline()
        o.NewOutline()
        for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)):
            o.Append(mm(x), mm(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(OUT)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
