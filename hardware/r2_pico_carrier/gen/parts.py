"""R2 Pico carrier board: every part, its footprint, its LCSC number and the net on each pad.
The one source of truth: the schematic (make_sch.py), the board (make_pcb.py) and the
JLCPCB BOM/CPL (make_fab.py) are all generated from this file. Checked by test_parts.py.

The Pico 2 plugs in, pins down, into two 1x20 female sockets:
  JP1 pin k = Pico pin k (1..20, the GP0 side); JP2 pin k = Pico pin 41-k (40..21).
Connectors keep the module's own pin order, so a straight Dupont cable fits:
  VL1-VL4 (VL53L0X GY-530) VIN GND SCL SDA GPIO1 XSHUT; US1-US5 (HC-SR04) VCC TRIG ECHO GND.
VL1-VL2 sit on the I2C bus itself (cables < 50 cm); VL3-VL4 behind the U1 repeater (> 50 cm).

Every LCSC number was checked on its jlcpcb.com part page (27 Oct 2026). MAKER gives the
maker and maker part number of each, for the PCBWay BOM (PCBWay does not use LCSC numbers).
"""
from dataclasses import dataclass, field


@dataclass
class Part:
    ref: str
    value: str
    footprint: str
    lcsc: str
    pads: dict = field(default_factory=dict)     # pad number -> net ("" = not connected)
    symbol: str = ""                              # KiCad lib:symbol for the schematic
    dnp: bool = False


R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
LCSC_R = {"1k": "C21190", "2k": "C22975", "2.2k": "C4190", "4.7k": "C23162", "33": "C23140"}

# Pico pin -> net. GP2-5 XSHUT, GP10-15/18-21 sonars, GP16/17 I2C, GP22 LEDs, GP26 button.
PICO_PIN_NET = {p: "" for p in range(1, 41)}
PICO_PIN_NET.update({p: "GND" for p in (3, 8, 13, 18, 23, 28, 33, 38)})
PICO_PIN_NET.update({4: "XSHUT1", 5: "XSHUT2", 6: "XSHUT3", 7: "XSHUT4",
                     14: "TRIG1", 15: "ECHO1_P", 16: "TRIG2", 17: "ECHO2_P",
                     19: "TRIG3", 20: "ECHO3_P", 21: "SDA", 22: "SCL",
                     24: "TRIG4", 25: "ECHO4_P", 26: "TRIG5", 27: "ECHO5_P",
                     29: "LED_DIN_P", 31: "BTN", 36: "+3V3", 39: "VSYS"})

PARTS = {}


def add(ref, value, footprint, lcsc, pads, symbol):
    PARTS[ref] = Part(ref, value, footprint, lcsc, {str(k): v for k, v in pads.items()}, symbol)


def resistor(ref, value, a, b):
    add(ref, value, R0603, LCSC_R[value], {1: a, 2: b}, "Device:R")


def cap(ref, value, a, b="GND"):
    big = value in ("10u", "22u")
    add(ref, value, C0805 if big else C0603,
        {"100n": "C14663", "10u": "C15850", "22u": "C45783"}[value], {1: a, 2: b}, "Device:C")


# --- Pico sockets -----------------------------------------------------------------
SOCKET20 = "Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical"
add("JP1", "Pico 2 pins 1-20", SOCKET20, "C50984", {k: PICO_PIN_NET[k] for k in range(1, 21)},
    "Connector_Generic:Conn_01x20")
add("JP2", "Pico 2 pins 40-21", SOCKET20, "C50984", {k: PICO_PIN_NET[41 - k] for k in range(1, 21)},
    "Connector_Generic:Conn_01x20")

# --- 5 V input: J1 -> F1 -> D1 -> +5V; +5V -> D2 -> VSYS; +5V -> D3 -> VLED -------------
add("J1", "5V in", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    "C474952", {1: "5V_IN", 2: "GND"}, "Connector:Screw_Terminal_01x02")  # KF128-5.08-2P
add("F1", "0.75A", "Fuse:Fuse_1206_3216Metric", "C976305", {1: "5V_IN", 2: "5V_FUSED"},
    "Device:Polyfuse")                                                    # BSMD1206-075-30V
SS34 = ("Diode_SMD:D_SMA", "C8678", "Device:D_Schottky")                  # pad 1 K, pad 2 A
for ref, k, a in (("D1", "+5V", "5V_FUSED"), ("D2", "VSYS", "+5V"), ("D3", "VLED", "+5V")):
    add(ref, "SS34", SS34[0], SS34[1], {1: k, 2: a}, SS34[2])
cap("C1", "22u", "+5V")
cap("C2", "100n", "+5V")
cap("C3", "10u", "VLED")
cap("C4", "10u", "+3V3")
add("D4", "green", "LED_SMD:LED_0603_1608Metric", "C72043", {1: "PWR_LED", 2: "+5V"}, "Device:LED")
resistor("R1", "1k", "PWR_LED", "GND")

# --- I2C: pull-ups on the short bus, U1 repeater to the long one ----------------------
resistor("R2", "4.7k", "SDA", "+3V3")
resistor("R3", "4.7k", "SCL", "+3V3")
# Port B (static low offset) on the Pico's bus, port A (clean ~0 V low) on the long cables:
# the datasheet's own "driving a short cable" example (master on B, cable on A)
add("U1", "PCA9517A", "Package_SO:VSSOP-8_3x3mm_P0.65mm", "C80799",      # PCA9517ADP (MSOP-8)
    {1: "+3V3", 2: "SCL_L", 3: "SDA_L", 4: "GND", 5: "+3V3", 6: "SDA", 7: "SCL", 8: "+3V3"},
    "Logic_LevelTranslator:TCA9517ADGK")
cap("C5", "100n", "+3V3")
resistor("R4", "2.2k", "SDA_L", "+3V3")
resistor("R5", "2.2k", "SCL_L", "+3V3")

# --- VL53L0X connectors ----------------------------------------------------------------
HDR6 = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
for n in range(1, 5):
    sda, scl = ("SDA", "SCL") if n <= 2 else ("SDA_L", "SCL_L")
    add(f"VL{n}", f"VL53L0X {n}", HDR6, "C37208",
        {1: "+3V3", 2: "GND", 3: scl, 4: sda, 5: "", 6: f"XSHUT{n}"}, "Connector_Generic:Conn_01x06")

# --- HC-SR04 connectors and ECHO dividers (1k ECHO -> pin, 2k pin -> GND) ---------------
HDR4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
for n in range(1, 6):
    add(f"US{n}", f"HC-SR04 {n}", HDR4, "C2691448",
        {1: "+5V", 2: f"TRIG{n}", 3: f"ECHO{n}", 4: "GND"}, "Connector_Generic:Conn_01x04")
    resistor(f"R{10 + n}", "1k", f"ECHO{n}", f"ECHO{n}_P")
    resistor(f"R{20 + n}", "2k", f"ECHO{n}_P", "GND")

# --- diagnostic LEDs: one WS2812B-2020 per connector (VL1..VL4, US1..US5) -----------------
resistor("R6", "33", "LED_DIN_P", "LED_DIN")
for k in range(1, 10):
    add(f"LED{k}", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", "C965555",
        {1: f"LED_D{k}" if k < 9 else "", 2: "GND", 3: "LED_DIN" if k == 1 else f"LED_D{k - 1}", 4: "VLED"},
        "LED:WS2812B-2020")
    cap(f"C{10 + k}", "100n", "VLED")

# --- display socket and button ---------------------------------------------------------
add("J2", "OLED SSD1306", "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical", "C2718488",
    {1: "GND", 2: "+3V3", 3: "SCL", 4: "SDA"}, "Connector_Generic:Conn_01x04")
add("SW1", "display", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884",
    {1: "BTN", 2: "GND"}, "Switch:SW_Push")

# --- M3 mounting holes -------------------------------------------------------------------
for k in range(1, 5):
    add(f"H{k}", "M3", "MountingHole:MountingHole_3.2mm_M3", "", {}, "Mechanical:MountingHole")

NETS = {n for p in PARTS.values() for n in p.pads.values() if n}

# LCSC number -> (maker, maker part number, type) for the PCBWay BOM
MAKER = {
    "C21190": ("UNI-ROYAL", "0603WAF1001T5E", "SMD"),
    "C22975": ("UNI-ROYAL", "0603WAF2001T5E", "SMD"),
    "C4190": ("UNI-ROYAL", "0603WAF2201T5E", "SMD"),
    "C23162": ("UNI-ROYAL", "0603WAF4701T5E", "SMD"),
    "C23140": ("UNI-ROYAL", "0603WAF330JT5E", "SMD"),
    "C14663": ("Samsung", "CL10B104KB8NNNC", "SMD"),
    "C15850": ("Samsung", "CL21A106KAYNNNE", "SMD"),
    "C45783": ("Samsung", "CL21A226MAQNNNE", "SMD"),
    "C8678": ("MDD", "SS34", "SMD"),
    "C976305": ("BHFUSE", "BSMD1206-075-30V", "SMD"),
    "C72043": ("Everlight", "19-217/GHC-YR1S2/3T", "SMD"),
    "C80799": ("NXP", "PCA9517ADP,118", "SMD"),
    "C965555": ("Worldsemi", "WS2812B-2020", "SMD"),
    "C318884": ("XKB Connection", "TS-1187A-B-A-B", "SMD"),
    "C50984": ("BOOMELE", "2.54-1*20PFemale", "THT"),
    "C37208": ("BOOMELE", "2.54-1x6P male header, straight", "THT"),
    "C2691448": ("XFCN", "PZ254V-11-04P", "THT"),
    "C2718488": ("BOOMELE", "2.54-1*4P female header", "THT"),
    "C474952": ("KEFA", "KF128-5.08-2P", "THT"),
}


def nets_of(ref):
    return PARTS[ref].pads
