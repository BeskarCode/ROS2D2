# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""FaceLock: with several faces the dome follows one, calmly: it keeps the first one while it is
roughly where it was, waits when it loses it, and only then picks another (and says so)."""

from r2_dome_tracker.control import FaceLock, SoundGate


def face(bearing, size=0.2, t=0.0):
    return (t, bearing, size)


def test_first_face_is_a_new_lock():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    got, new, waiting = lock.update([face(10, 0.2)], 0.0)
    assert got[1] == 10 and new and not waiting


def test_keeps_its_face_even_when_a_bigger_one_appears():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10, 0.2)], 0.0)
    got, new, _ = lock.update([face(12, 0.2), face(-30, 0.5)], 0.1)   # someone bigger came in
    assert got[1] == 12 and not new


def test_follows_its_face_as_it_moves_in_small_steps():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(0)], 0.0)
    for i, b in enumerate([8, 16, 24, 32]):              # walking across, 8 deg per picture
        got, new, _ = lock.update([face(b), face(-40, 0.6)], 0.1 * (i + 1))
        assert got[1] == b and not new


def test_waits_calmly_when_it_loses_its_face():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10)], 0.0)
    got, new, waiting = lock.update([face(-40, 0.6)], 0.5)   # only another face now
    assert got is None and not new and waiting
    got, new, waiting = lock.update([face(-40, 0.6)], 1.9)
    assert got is None and waiting


def test_its_face_back_within_the_wait_is_the_same_one():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10)], 0.0)
    lock.update([], 1.0)
    got, new, waiting = lock.update([face(14)], 1.5)
    assert got[1] == 14 and not new and not waiting


def test_after_the_wait_it_picks_the_biggest_other_face():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10)], 0.0)
    lock.update([face(-40, 0.3), face(50, 0.5)], 1.0)
    got, new, waiting = lock.update([face(-40, 0.3), face(50, 0.5)], 2.1)
    assert got[1] == 50 and new and not waiting


def test_nobody_after_the_wait_is_free_again():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10)], 0.0)
    got, new, waiting = lock.update([], 2.5)
    assert got is None and not new and not waiting
    got, new, _ = lock.update([face(-5)], 3.0)                 # a face again: a new lock
    assert got[1] == -5 and new


def test_reset_forgets_the_face():
    lock = FaceLock(gate_deg=15, calm_s=2.0)
    lock.update([face(10)], 0.0)
    lock.reset()
    got, new, _ = lock.update([face(40)], 0.1)
    assert got[1] == 40 and new


def test_sound_gate_plays_at_most_every_min_gap():
    g = SoundGate(min_gap_s=3.0)
    assert g.ready(0.0) and not g.ready(1.0) and not g.ready(2.9) and g.ready(3.1)
