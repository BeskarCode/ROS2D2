# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The head of Patrol and Free roam (wander_core), without ROS: chance fixed with a seed, time given."""
import math
import random

import pytest

pytest.importorskip("r2_dome_tracker.control")
from r2_dome_tracker.control import Gains  # noqa: E402
from r2_nav.nav_core import parse_nav  # noqa: E402
from r2_nav.wander_core import Wander  # noqa: E402

DT = 0.1


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def wcfg(**over):
    c = parse_nav("")["wander"]
    c.update(over)
    return c


def make(radius=True, seed=1, pose=(0.0, 0.0, 0.0), **over):
    w = Wander(wcfg(**over), Gains(), random.Random(seed), radius)
    w.start(0.0, pose)
    return w


def turns_right(speed, gains=Gains()):
    """Does this DM: speed turn the dome towards + (right)? (DomeEstimate's sign convention)"""
    return speed * (-1 if gains.invert else 1) > 0


def run(w, t0, t1, pose=(0.0, 0.0, 0.0), nav_state="forward", faces=None, dome_deg=0.0):
    outs, t = [], t0
    while t < t1 - 1e-9:
        f = faces(t) if callable(faces) else (faces or [])
        outs.append((t, w.step(t, pose, nav_state, f, dome_deg)))
        t += DT
    return outs


def test_walk_turns_within_turn_deg():
    w = make(pause_chance=0.0)
    outs = run(w, 0.0, 70.0)
    heads = [o.heading for _, o in outs]
    changes = [math.degrees(abs(wrap(b - a))) for a, b in zip(heads, heads[1:]) if abs(wrap(b - a)) > 1e-9]
    assert len(changes) >= 3                                    # 8-20 s apart over 70 s
    assert all(30 - 1e-6 <= c <= 120 + 1e-6 for c in changes)
    assert all(o.state == "walk" and not o.hold for _, o in outs)


def test_pause_chance_goes_to_look_and_back():
    w = make(pause_chance=1.0, pause_s=[3, 3], turn_every_s=[8, 8])
    outs = run(w, 0.0, 12.5)
    look = [t for t, o in outs if o.state == "look"]
    assert look and look[0] == pytest.approx(8.0, abs=DT)
    assert all(o.hold for _, o in outs if o.state == "look")
    assert look[-1] - look[0] == pytest.approx(3.0, abs=DT + 1e-6)   # 3 s of looking round
    assert outs[-1][1].state == "walk" and not outs[-1][1].hold


def test_idle_sound_from_list():
    w = make(pause_chance=1.0, turn_every_s=[8, 8], idle_sounds=["S1:$15"])
    outs = run(w, 0.0, 9.0)
    sounds = [(t, s) for t, o in outs for s in o.sounds]
    assert sounds == [(pytest.approx(8.0, abs=DT), "S1:$15")]


def face_at(bearing, size):
    return lambda t: [(t, bearing, size)]


def test_greets_new_close_face_once():
    w = make()
    outs = run(w, 0.0, 3.0, faces=face_at(0.0, 0.1))
    assert outs[0][1].state == "greet" and outs[0][1].hold
    assert [s for _, o in outs for s in o.sounds] == ["S1:$12"]
    assert all(o.state == "greet" for _, o in outs)


def test_greet_cooldown():
    w = make(greet_cooldown_s=20, greet_s=2)
    run(w, 0.0, 1.0, faces=face_at(0.0, 0.1))                    # hello
    run(w, 1.0, 5.0)                                             # gone (2 s calm), back to walking
    outs = run(w, 5.0, 8.0, faces=face_at(40.0, 0.1))            # someone else, too soon
    assert not [s for _, o in outs for s in o.sounds] and all(o.state != "greet" for _, o in outs)
    run(w, 8.0, 12.0)
    outs = run(w, 21.0, 22.0, faces=face_at(-40.0, 0.1))         # 20 s after the first hello
    assert outs[0][1].state == "greet" and outs[0][1].sounds == ["S1:$12"]


def test_small_face_no_greet():
    w = make()
    outs = run(w, 0.0, 2.0, faces=face_at(20.0, 0.05))
    assert all(o.state == "walk" and not o.sounds for _, o in outs)
    assert turns_right(outs[-1][1].dome)                        # the dome looks at it all the same


def test_greet_ends_when_face_leaves():
    w = make()                                                   # FaceLock waits 2 s (its default)
    h0 = run(w, 0.0, 1.0, faces=face_at(0.0, 0.1))[-1][1].heading
    outs = run(w, 1.0, 4.0)
    walking = [(t, o) for t, o in outs if o.state == "walk"]
    assert walking and walking[0][0] == pytest.approx(3.0, abs=0.15)   # after the 2 s calm
    turned = math.degrees(abs(wrap(walking[0][1].heading - h0)))
    assert 180 - 30 - 1e-6 <= turned <= 180 + 1e-6                   # the other way, give or take turn_deg[0]
    assert not walking[0][1].hold


def test_blocked_turns_away():
    w = make(pause_chance=0.0, blocked_s=3)
    h0 = w.step(0.0, (0.0, 0.0, 0.0), "forward", [], 0.0).heading
    outs = run(w, 0.1, 3.5, nav_state="searching")
    away = [(t, o) for t, o in outs if o.state == "turn_away"]
    assert len(away) == 1 and away[0][0] == pytest.approx(3.1, abs=DT + 1e-6)
    assert 120 - 1e-6 <= math.degrees(abs(wrap(away[0][1].heading - h0))) <= 180 + 1e-6
    assert outs[-1][1].state == "walk"


def test_radius_brings_it_home():
    w = make(radius=True)
    o = w.step(0.1, (3.0, 0.0, 0.0), "forward", [], 0.0)       # 3 m out, heading further away
    assert abs(math.degrees(wrap(o.heading - math.pi))) <= 30 + 1e-6
    assert o.home_dist == pytest.approx(3.0)


def test_free_has_no_radius():
    w = make(radius=False)
    o = w.step(0.1, (3.0, 0.0, 0.0), "forward", [], 0.0)
    assert o.heading == pytest.approx(0.0)


@pytest.mark.parametrize("seed", range(8))
def test_home_heading_wraps(seed):
    w = make(radius=True, seed=seed)
    o = w.step(0.1, (3.0, 0.01, 0.0), "forward", [], 0.0)      # home is just past -180 / +180
    home = math.atan2(-0.01, -3.0)
    assert math.degrees(abs(wrap(o.heading - home))) <= 30 + 1e-6
    assert -math.pi <= o.heading <= math.pi


def test_no_faces_dome_back_to_front():
    w = make()
    o = w.step(0.1, (0.0, 0.0, 0.0), "forward", [], 30.0)
    assert o.dome != 0 and not turns_right(o.dome)             # turned right: back left, to the front
    o = w.step(0.2, (0.0, 0.0, 0.0), "forward", [], -30.0)
    assert turns_right(o.dome)
    assert w.step(0.3, (0.0, 0.0, 0.0), "forward", [], 2.0).dome == 0


def test_look_sweeps_dome():
    w = make(pause_chance=1.0, turn_every_s=[8, 8], pause_s=[6, 6])
    outs = run(w, 0.0, 8.5)
    assert outs[-1][1].state == "look" and outs[-1][1].dome != 0     # looks round with no face
    o = w.step(8.6, (0.0, 0.0, 0.0), "forward", [], 46.0)
    assert not turns_right(o.dome)                              # at the right end: back the other way
    o = w.step(8.7, (0.0, 0.0, 0.0), "forward", [], -46.0)
    assert turns_right(o.dome)


def test_no_pose_keeps_heading_and_skips_radius():
    w = make(pause_chance=0.0, turn_every_s=[8, 8])
    h0 = w.step(0.0, (0.0, 0.0, 0.0), "forward", [], 0.0).heading
    outs = run(w, 0.1, 20.0, pose=None)
    assert all(o.heading == h0 for _, o in outs)
    assert all(o.home_dist is None for _, o in outs)


def test_heading_none_until_a_pose():
    w = Wander(wcfg(), Gains(), random.Random(1), True)
    w.start(0.0, None)
    assert w.step(0.1, None, None, [], 0.0).heading is None
    o = w.step(0.2, (1.0, 2.0, 0.7), "forward", [], 0.0)
    assert o.heading == pytest.approx(0.7) and o.home_dist == pytest.approx(0.0)   # the start is where it is now


def test_wander_active_only_in_its_modes_with_auto_on():
    from r2_nav.wander_core import wander_active
    assert wander_active("patrol", True) and wander_active("free", True)
    assert not wander_active("patrol", False)
    assert not wander_active("forward", True) and not wander_active("", True) and not wander_active(None, True)


def test_mode_off_stops_dome_once():
    from r2_nav.wander_core import leave_outputs
    assert leave_outputs(True, False) == [("dome", 0)]     # leaving: one stop for the dome
    assert leave_outputs(False, False) == []               # then silence (the dome tracker is free)
    assert leave_outputs(False, True) == [] and leave_outputs(True, True) == []


def test_blocked_counts_through_flicker():
    w = make(pause_chance=0.0, blocked_s=3)
    w.step(0.0, (0.0, 0.0, 0.0), "forward", [], 0.0)
    outs = run(w, 0.1, 4.0, nav_state=None)
    # the navigator flips between searching and forward every step while it creeps on
    w2 = make(pause_chance=0.0, blocked_s=3)
    states, t, away = ["searching", "forward"], 0.0, []
    for i in range(40):
        o = w2.step(t, (0.0, 0.0, 0.0), states[i % 2], [], 0.0)
        if o.state == "turn_away":
            away.append(t)
        t += DT
    assert away and away[0] == pytest.approx(3.0, abs=0.2)
    assert not [o for _, o in outs if o.state == "turn_away"]
