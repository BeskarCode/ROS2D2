# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_nav.patrol import Patrol, parse_route

A, B, C = (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)


def test_loops_in_order():
    p = Patrol()
    p.set([A, B, C])
    assert p.current() == A
    assert [p.after("arrived") for _ in range(4)] == [B, C, A, B]


def test_a_point_it_cannot_reach_is_skipped():
    p = Patrol()
    p.set([A, B, C])
    assert p.after("gave up") == B
    assert p.after("arrived") == C          # arriving resets the count


def test_none_reachable_stops():
    p = Patrol()
    p.set([A, B])
    assert p.after("gave up") == B
    assert p.after("gave up") is None
    assert p.current() is None


def test_empty_route():
    p = Patrol()
    p.set([])
    assert p.current() is None and p.after("arrived") is None


def test_single_point_repeats():
    p = Patrol()
    p.set([B])
    assert p.after("arrived") == B


def test_other_states_keep_the_point():
    p = Patrol()
    p.set([A, B])
    assert p.after("going") == A


def test_parse_route():
    assert parse_route("[[0, 0], [1.5, -2]]") == [(0.0, 0.0), (1.5, -2.0)]
    assert parse_route("[]") == []
    for bad in ("nope", "[[1]]", '[["a", 1]]', "{}", "[[1, 2, 3]]"):
        assert parse_route(bad) is None
