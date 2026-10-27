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
    assert [nets_of("J2")[str(p)] for p in range(1, 5)] == ["GND", "+3V3", "SCL", "SDA"]
    assert [nets_of("J1")[str(p)] for p in range(1, 3)] == ["5V_IN", "GND"]


def test_long_group():
    assert {"VL1", "VL2", "J2", "U1"} <= refs_on("SDA") and {"VL3", "VL4"}.isdisjoint(refs_on("SDA"))
    assert {"VL3", "VL4", "U1"} <= refs_on("SDA_L") and {"VL1", "VL2", "J2"}.isdisjoint(refs_on("SDA_L"))
    assert {"VL1", "VL2", "J2", "U1"} <= refs_on("SCL") and {"VL3", "VL4", "U1"} <= refs_on("SCL_L")


def test_pico_pins():
    want = {4: "XSHUT1", 5: "XSHUT2", 6: "XSHUT3", 7: "XSHUT4",
            14: "TRIG1", 15: "ECHO1_P", 16: "TRIG2", 17: "ECHO2_P", 19: "TRIG3", 20: "ECHO3_P",
            21: "SDA", 22: "SCL", 24: "TRIG4", 25: "ECHO4_P", 26: "TRIG5", 27: "ECHO5_P",
            29: "LED_DIN_P", 31: "BTN", 36: "+3V3", 39: "VSYS"}
    want.update({p: "GND" for p in GND_PINS})
    assert {p: n for p, n in PICO_PIN_NET.items() if n} == want
    assert PICO_PIN_NET[40] == "" and PICO_PIN_NET[30] == ""     # VBUS and RUN left alone


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
    assert refs_on("5V_IN") == {"J1", "F1"}
    f1_out = next(n for n in PARTS["F1"].pads.values() if n != "5V_IN")
    assert refs_on(f1_out) == {"F1", "D1"} and PARTS["D1"].pads["2"] == f1_out    # anode
    assert PARTS["D1"].pads["1"] == "+5V"                                          # cathode
    assert refs_on("VSYS") == {"D2", "JP2"} and PARTS["D2"].pads == {"1": "VSYS", "2": "+5V"}
    vled = refs_on("VLED")
    assert "D3" in vled and PARTS["D3"].pads == {"1": "VLED", "2": "+5V"}
    assert all(r.startswith(("LED", "C", "D3")) for r in vled)
    assert not refs_on("VBUS")


def test_led_chain():
    r = next(x for x in refs_on("LED_DIN_P") if x.startswith("R"))
    assert PARTS[r].value == "33" and refs_on("LED_DIN_P") == {r, "JP2"}
    din = {"LED1": next(n for n in PARTS[r].pads.values() if n != "LED_DIN_P")}
    for k in range(1, 10):
        led = PARTS[f"LED{k}"]
        # WS2812B-2020: 1 DOUT, 2 VSS, 3 DIN, 4 VDD
        assert led.pads["3"] == (din["LED1"] if k == 1 else f"LED_D{k - 1}")
        assert led.pads["1"] == (f"LED_D{k}" if k < 9 else "")
        assert led.pads["2"] == "GND" and led.pads["4"] == "VLED"


def test_every_part_has_lcsc_and_footprint():
    for ref, part in PARTS.items():
        lib, name = part.footprint.split(":")
        assert os.path.isfile(os.path.join(KICAD_FP, f"{lib}.pretty", f"{name}.kicad_mod")), ref
        if not part.dnp and not ref.startswith("H"):
            assert re.fullmatch(r"C\d+", part.lcsc), ref


@pytest.mark.parametrize("net", ["+5V", "+3V3", "VLED"])
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
