import io

import pytest

from r2_sim import fake_mega as fm


class Port:
    def __init__(self):
        self.out = []

    def write(self, data):
        self.out.append(data.decode())


@pytest.fixture
def mega():
    fm.ser, fm.log = Port(), io.StringIO()
    fm.auto_on, fm.reason, fm.mode = False, "boot", ""
    fm.reset_bindings()
    return fm


def said(m):
    out, m.ser.out = [x.strip() for x in m.ser.out], []
    return out


def test_default_button_is_goto(mega):
    mega.on_control("button")
    assert said(mega) == ["AUTO ON goto"]
    mega.on_control("button")
    assert said(mega) == ["AUTO OFF button"]


def test_bind_and_combo_press_semantics(mega):
    mega.on_line("ROS:BIND:CLEAR")
    mega.on_line("ROS:BIND:FOOT_UP,follow")
    mega.on_line("ROS:BIND:DOME_UP_L1,patrol")
    assert said(mega) == ["BIND CLEAR", "BIND OK FOOT_UP follow", "BIND OK DOME_UP_L1 patrol"]
    mega.on_control("button")                      # FOOT_PS_L2 is unbound now
    mega.on_control("combo FOOT_DOWN")             # unbound combo
    assert said(mega) == []
    mega.on_control("combo FOOT_UP")
    mega.on_control("combo DOME_UP_L1")            # other mode: switches
    mega.on_control("combo DOME_UP_L1")            # same mode: off
    assert said(mega) == ["AUTO ON follow", "AUTO ON patrol", "AUTO OFF button"]


def test_bind_errors_and_reset(mega):
    mega.on_line("ROS:BIND:NOPE,goto")
    mega.on_line("ROS:BIND:DOME_PS_L2,goto")
    mega.on_line("ROS:BIND:FOOT_UP,fly")
    assert said(mega) == ["ERR unknown combo", "ERR unknown combo", "ERR unknown mode"]
    mega.on_line("ROS:BIND:CLEAR")
    for c in fm.COMBOS[1:9]:
        mega.on_line(f"ROS:BIND:{c},goto")
    said(mega)
    mega.on_line(f"ROS:BIND:{fm.COMBOS[9]},goto")
    assert said(mega) == ["ERR BIND FULL"]
    mega.on_line(f"ROS:BIND:{fm.COMBOS[1]},none")
    assert said(mega) == [f"BIND OK {fm.COMBOS[1]} none"]
    mega.on_line("ROS:BIND:RESET")
    assert said(mega) == ["BIND RESET"]
    mega.on_control("button")
    assert said(mega) == ["AUTO ON goto"]


def test_state_query_and_reset_word(mega):
    mega.on_line("ROS:AUTO:?")
    assert said(mega) == ["AUTO OFF boot"]
    mega.on_line("ROS:BIND:CLEAR")
    mega.on_control("reset")
    said(mega)
    mega.on_control("button")
    assert said(mega) == ["AUTO ON goto"]
