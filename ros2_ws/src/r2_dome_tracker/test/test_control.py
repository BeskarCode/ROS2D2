from r2_dome_tracker.control import DomeTracker, Gains, face_error


def tracker(**kw):
    return DomeTracker(Gains(invert=False, **kw))


def test_face_error():
    assert face_error(320, 640) == 0
    assert face_error(0, 640) == -1
    assert face_error(640, 640) == 1


def test_no_face_no_movement():
    assert tracker().speed(now=10.0) == 0


def test_centred_face_stays_in_deadzone():
    t = tracker()
    t.face(0.05, 1.0)
    assert t.speed(1.0) == 0


def test_face_at_right_edge_turns_right_fast():
    t = tracker()
    for i in range(10):                    # held still at the edge: smoothing converges to 1
        t.face(1.0, 1.0 + i * 0.05)
    assert t.speed(1.45) == 58


def test_face_left_turns_left():
    t = tracker()
    for i in range(10):
        t.face(-0.6, 1.0 + i * 0.05)
    s = t.speed(1.45)
    assert -58 < s < -18


def test_invert_flips_direction():
    a, b = DomeTracker(Gains(invert=False)), DomeTracker(Gains(invert=True))
    for i in range(10):
        a.face(0.8, i * 0.05)
        b.face(0.8, i * 0.05)
    assert a.speed(0.45) == -b.speed(0.45) != 0


def test_stops_when_face_is_lost():
    t = tracker()
    for i in range(10):
        t.face(1.0, i * 0.05)
    assert t.speed(0.45) != 0
    assert t.speed(0.45 + 0.3) == 0       # older than lost_after (0.2 s)


def test_brakes_when_face_comes_back_to_centre():
    # Face on the right but moving fast towards the centre (the dome catching up): no push
    t = tracker()
    t.face(0.6, 0.00)
    t.face(0.3, 0.05)
    t.face(0.2, 0.10)
    assert t.speed(0.10) == 0


def test_speed_never_exceeds_max():
    t = tracker()
    t.face(1.0, 0.00)
    t.face(1.0, 0.01)
    t.rate = 50.0                          # absurd face speed
    assert abs(t.speed(0.01)) == 58
