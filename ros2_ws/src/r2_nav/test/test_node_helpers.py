# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
import json

from r2_nav.nav_core import Decision, clamp_param, ramp, state_json


def test_ramp():
    assert ramp(0.0, 1.0, 0.05) == 0.05
    assert ramp(0.3, 0.0, 0.05) == 0.25
    assert ramp(0.1, 0.12, 0.05) == 0.12


def test_param_clamped():
    assert clamp_param("max_speed", 5) == 0.4
    assert clamp_param("max_turn_deg", 90) == 34
    assert clamp_param("give_up_after", 0) == 1
    assert clamp_param("on_blocked", "wait") == "wait"


def test_state_json():
    d = Decision(v=0.2, w=-0.1, state="going", why="x", heading=0.3, tries=1, stops={"tof_front": 0.32})
    j = json.loads(state_json(d, (2.0, 1.0), heading_odom=1.2, filtered={"tof_front": None}, raw={"tof_front": 0.5}))
    for k in ("state", "why", "v", "w", "heading", "tries", "goal", "stops", "filtered", "raw"):
        assert k in j
    assert j["goal"] == [2.0, 1.0] and j["filtered"]["tof_front"] is None and j["heading"] == 1.2
    assert json.loads(state_json(d, None, None, {}, {}))["goal"] is None
