"""The carrier board's parts and nets (parts.py), checked before any drawing is made.
Run with KiCad's Python:  $KPY -m pytest hardware/r2_pico_carrier/gen
"""
import os
import re

import pytest

from parts import PARTS, PICO_PIN_NET, nets_of

KICAD_FP = os.environ.get(
    "KICAD_FP", r"C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints")
GND_PINS = (3, 8, 13, 18, 23, 28, 33, 38)
# Status LED k (LED1-4 = VL1-4, LED5-9 = US1-5): Pico pin -> its net. GPIOs nearest each
# connector: VL1-VL4 = GP28, GP27, GP22, GP9; US1-US5 = GP0, GP1, GP6, GP7, GP8
LED_PICO_PIN = {34: "STAT1", 32: "STAT2", 29: "STAT3", 12: "STAT4",
                1: "STAT5", 2: "STAT6", 9: "STAT7", 10: "STAT8", 11: "STAT9"}


def pads_on(net):
    """{(ref, pad)} touching a net."""
    return {(r, p) for r, part in PARTS.items() for p, n in part.pads.items() if n == net}


def refs_on(net):
    return {r for r, _ in pads_on(net)}


def test_connector_pin_orders():
    for n, (sda, scl) in enumerate([("SDA", "SCL")] * 2 + [("SDA_L", "SCL_L")] * 2, 1):
        assert [nets_of(f"VL{n}")[str(p)] for p in range(1, 7)] == ["+3V3", "GND", scl, sda, "", f"XSHUT{n}"]
    for n in range(1, 6):
        assert [nets_of(f"US{n}")[str(p)] for p in range(1, 5)] == ["+5V", f"TRIG{n}", f"ECHO{n}", "GND"]
    # the OLED module's own pin order (HS96L03W2C03 datasheet: GND VCC SCL SDA)
    assert [nets_of("J2")[str(p)] for p in range(1, 5)] == ["GND", "+3V3", "SCL", "SDA"]
    assert PARTS["J2"].footprint.endswith("PinSocket_1x04_P2.54mm_Vertical")   # the OLED plugs in
    assert [nets_of("J1")[str(p)] for p in range(1, 3)] == ["5V_IN", "GND"]


def test_long_group():
    assert {"VL1", "VL2", "J2", "U1"} <= refs_on("SDA") and {"VL3", "VL4"}.isdisjoint(refs_on("SDA"))
    assert {"VL3", "VL4", "U1"} <= refs_on("SDA_L") and {"VL1", "VL2", "J2"}.isdisjoint(refs_on("SDA_L"))
    assert {"VL1", "VL2", "J2", "U1"} <= refs_on("SCL") and {"VL3", "VL4", "U1"} <= refs_on("SCL_L")


def test_pico_pins():
    want = {4: "XSHUT1", 5: "XSHUT2", 6: "XSHUT3", 7: "XSHUT4",
            14: "TRIG1", 15: "ECHO1_P", 16: "TRIG2", 17: "ECHO2_P", 19: "TRIG3", 20: "ECHO3_P",
            21: "SDA", 22: "SCL", 24: "TRIG4", 25: "ECHO4_P", 26: "TRIG5", 27: "ECHO5_P",
            30: "RUN", 31: "BTN", 36: "+3V3", 39: "VSYS"}
    want.update(LED_PICO_PIN)
    want.update({p: "GND" for p in GND_PINS})
    assert {p: n for p, n in PICO_PIN_NET.items() if n} == want
    assert PICO_PIN_NET[40] == ""                 # VBUS left alone: the Pi's USB never meets our 5 V


def test_pico_sockets_follow_the_pico():
    for pin in range(1, 21):
        assert nets_of("JP1")[str(pin)] == PICO_PIN_NET[pin]
    for k in range(1, 21):
        assert nets_of("JP2")[str(k)] == PICO_PIN_NET[41 - k]


def test_echo_divider():
    for n in range(1, 6):
        raw, safe = f"ECHO{n}", f"ECHO{n}_P"
        top = [r for r in refs_on(raw) if r.startswith("R")]
        assert refs_on(raw) == {f"US{n}", *top} and len(top) == 1
        assert PARTS[top[0]].value == "1k" and refs_on(safe) >= {top[0]}
        bottom = [r for r in refs_on(safe) if r.startswith("R") and r != top[0]]
        assert len(bottom) == 1 and PARTS[bottom[0]].value == "2k"
        assert "GND" in PARTS[bottom[0]].pads.values()
        assert not any(r.startswith("JP") for r in refs_on(raw))      # 5 V never reaches the Pico


def test_power_path():
    """Terminal J1 and USB-C J5 each through their own diode (neither feeds the other), then
    together through the fuse to +5V; +5V -> D2 -> VSYS."""
    assert refs_on("5V_IN") == {"J1", "D1"} and PARTS["D1"].pads == {"1": "5V_OR", "2": "5V_IN"}
    assert refs_on("VBUS_C") == {"J5", "D5"} and PARTS["D5"].pads == {"1": "5V_OR", "2": "VBUS_C"}
    assert refs_on("5V_OR") == {"D1", "D5", "F1"} and set(PARTS["F1"].pads.values()) == {"5V_OR", "+5V"}
    assert refs_on("VSYS") == {"D2", "JP2"} and PARTS["D2"].pads == {"1": "VSYS", "2": "+5V"}
    assert not refs_on("VLED") and "D3" not in PARTS        # no LED rail any more
    assert not refs_on("VBUS")


def test_usb_c_power_only():
    """Any charger gives 5 V to a sink with 5.1k on each CC; data and SBU pins left free."""
    j5 = PARTS["J5"].pads
    assert PARTS["J5"].footprint == "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
    assert all(j5[p] == "VBUS_C" for p in ("A4", "A9", "B4", "B9"))
    assert all(j5[p] == "GND" for p in ("A1", "A12", "B1", "B12", "SH"))
    assert all(j5[p] == "" for p in ("A6", "A7", "B6", "B7", "A8", "B8"))
    for cc in ("A5", "B5"):
        r = [x for x in refs_on(j5[cc]) if x.startswith("R")]
        assert refs_on(j5[cc]) == {"J5", *r} and len(r) == 1 and PARTS[r[0]].value == "5.1k"
        assert "GND" in PARTS[r[0]].pads.values()
    assert j5["A5"] != j5["B5"]                                # one resistor per CC


def test_expansion():
    """Qwiic/STEMMA QT (JST-SH: GND 3V3 SDA SCL) and a 2.54 mm header 5V GND 3V3 SCL SDA RUN,
    both on the short I2C bus (the one with the pull-ups)."""
    assert [nets_of("J3")[str(p)] for p in range(1, 5)] == ["GND", "+3V3", "SDA", "SCL"]
    assert PARTS["J3"].footprint == "Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical"
    assert [nets_of("J4")[str(p)] for p in range(1, 7)] == ["+5V", "GND", "+3V3", "SCL", "SDA", "RUN"]
    assert refs_on("RUN") == {"J4", "JP2"}


def test_status_leds():
    """One plain 0603 LED per connector, each on its own GPIO: pin -> 1k -> anode, cathode -> GND."""
    for k in range(1, 10):
        led = PARTS[f"LED{k}"]
        assert led.footprint == "LED_SMD:LED_0603_1608Metric" and led.lcsc == PARTS["D4"].lcsc
        assert led.pads == {"1": "GND", "2": f"STAT{k}_A"}                 # pad 1 = cathode
        r = [x for x in refs_on(f"STAT{k}_A") if x.startswith("R")]
        assert len(r) == 1 and PARTS[r[0]].value == "1k"
        assert set(PARTS[r[0]].pads.values()) == {f"STAT{k}", f"STAT{k}_A"}
        assert refs_on(f"STAT{k}") == {r[0], "JP1" if k in (4, 5, 6, 7, 8, 9) else "JP2"}
    assert not any(n.startswith("LED_D") for p in PARTS.values() for n in p.pads.values())


def test_every_part_has_lcsc_and_footprint():
    for ref, part in PARTS.items():
        lib, name = part.footprint.split(":")
        assert os.path.isfile(os.path.join(KICAD_FP, f"{lib}.pretty", f"{name}.kicad_mod")), ref
        if not part.dnp and not ref.startswith("H"):
            assert re.fullmatch(r"C\d+", part.lcsc), ref


@pytest.mark.parametrize("net", ["+5V", "+3V3"])
def test_rails_have_decoupling(net):
    assert any(r.startswith("C") for r in refs_on(net))


def test_schematic_matches_parts(tmp_path):
    """The generated schematic (make_sch.py) connects exactly what parts.py says."""
    import subprocess
    import xml.etree.ElementTree as ET
    here = os.path.dirname(os.path.abspath(__file__))
    sch = os.path.join(here, "..", "r2_pico_carrier.kicad_sch")
    cli = os.path.join(os.path.dirname(os.path.dirname(KICAD_FP.rstrip(r"\/"))), "..", "bin", "kicad-cli.exe")
    out = tmp_path / "net.xml"
    subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out), sch], check=True,
                   capture_output=True)
    got = {}
    for net in ET.parse(out).getroot().iter("net"):
        for node in net.iter("node"):
            if not node.get("ref").startswith("#"):
                got[(node.get("ref"), node.get("pin"))] = net.get("name").lstrip("/")
    want = {(r, p): n for r, part in PARTS.items() for p, n in part.pads.items() if n}
    assert {k: v for k, v in got.items() if not v.startswith("unconnected-")} == want


def test_repeater_sides():
    """PCA9517A: port B has the static low offset, port A drives a clean ~0 V low (datasheet,
    'typical application driving a short cable': master on B, cable on A). So the Pico's short
    bus is on B and the long cables to VL3-VL4 are on A."""
    u1 = PARTS["U1"].pads
    assert (u1["2"], u1["3"]) == ("SCL_L", "SDA_L")       # SCLA, SDAA: the long bus
    assert (u1["7"], u1["6"]) == ("SCL", "SDA")           # SCLB, SDAB: the Pico's bus
    assert u1["1"] == u1["8"] == u1["5"] == "+3V3"        # VCCA, VCCB, EN
