# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_web.lidar_usb_api import NOT_INSTALLED, set_usb, usb_state


def fake(answers):
    calls = []

    def run(arg):
        calls.append(arg)
        return answers[arg]
    return run, calls


def test_state_passes_the_helper_answer():
    run, _ = fake({"state": (0, "disconnected")})
    assert usb_state(run) == (200, {"state": "disconnected"})


def test_state_without_the_sudoers_rule_says_how_to_install():
    run, _ = fake({"state": (1, "sudo: a password is required")})
    assert usb_state(run) == (200, {"state": None, "error": NOT_INSTALLED})


def test_off_stops_the_motor_first():
    order = []
    run, calls = fake({"off": (0, "disconnected")})
    code, body = set_usb(False, run=lambda a: (order.append(a), run(a))[1], stop_motor=lambda: order.append("stop"))
    assert (code, body) == (200, {"state": "disconnected"}) and order == ["stop", "off"]


def test_on_does_not_touch_the_motor():
    stopped = []
    run, calls = fake({"on": (0, "connected")})
    assert set_usb(True, run=run, stop_motor=lambda: stopped.append(1)) == (200, {"state": "connected"})
    assert calls == ["on"] and stopped == []


def test_helper_failure_is_a_409_with_its_line():
    run, _ = fake({"on": (1, "r2-lidar-usb: it was not disconnected here: unplug and plug the cable")})
    code, body = set_usb(True, run=run)
    assert code == 409 and "unplug and plug" in body["error"]


def test_connected_must_be_a_bool():
    assert set_usb("yes")[0] == 400
