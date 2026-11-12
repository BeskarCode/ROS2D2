# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_nav.lidar_gate import WAIT_S, LidarGate


def test_gate_waits_for_the_first_scan():
    g = LidarGate(policy="with_modes")
    g.activate(10.0)
    assert not g.ready(11.0)
    g.on_scan(11.5)
    assert g.ready(11.6)


def test_gate_gives_up_after_3_s():
    assert WAIT_S == 3.0
    g = LidarGate(policy="with_modes")
    g.activate(10.0)
    assert not g.ready(12.9) and g.ready(13.0)


def test_gate_never_blocks_with_always_or_off():
    for policy in ("always", "off"):
        g = LidarGate(policy=policy)
        g.activate(0.0)
        assert g.ready(0.0)


def test_scan_before_activation_does_not_count():
    g = LidarGate(policy="with_modes")
    g.on_scan(9.0)
    g.activate(10.0)
    assert not g.ready(10.5)


def test_reset_needs_a_new_activation():
    g = LidarGate(policy="with_modes")
    g.activate(0.0)
    g.on_scan(0.5)
    g.reset()
    g.activate(10.0)
    assert not g.ready(10.1)
