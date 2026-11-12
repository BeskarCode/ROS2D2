# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from r2_nav.lidar_gate import WAIT_S, LidarGate


def test_gate_waits_for_the_first_scan():
    g = LidarGate(policy="with_modes")
    g.activate(10.0)
    assert not g.ready(11.0)
    g.on_scan(11.5)
    assert g.ready(11.6)


def test_gate_gives_up_after_5_s():
    # 5 s (Fernando): start_motor plus spin-up takes about 4 s on the C1
    assert WAIT_S == 5.0
    g = LidarGate(policy="with_modes")
    g.activate(10.0)
    assert not g.ready(14.9) and g.ready(15.0)


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


def test_update_arms_on_the_rising_edge_only():
    g = LidarGate(policy="with_modes")
    g.update(0.0, False)
    assert not g.ready(0.0)                   # not driving: never ready to drive
    g.update(10.0, True)                       # follow chosen AND auto on: arm here
    assert not g.ready(11.0)
    g.update(12.0, True)                       # still on: no re-arm
    assert g.ready(15.0)


def test_mode_first_then_auto_later_still_waits():
    g = LidarGate(policy="with_modes")
    for t in range(0, 20):                     # follow chosen at 0, auto (PS+L2) only at 20
        g.update(float(t), False)
    g.update(20.0, True)
    assert not g.ready(21.0)
    g.on_scan(22.0)
    assert g.ready(22.1)


def test_leaving_and_coming_back_waits_again():
    g = LidarGate(policy="with_modes")
    g.update(0.0, True); g.on_scan(1.0)
    assert g.ready(1.1)
    g.update(5.0, False)                       # another mode owns the feet (motor may stop)
    g.update(20.0, True)                       # back: wait again
    assert not g.ready(20.5)
