# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The node imports rclpy (not on the PC): check its wiring as text, and that the droid starts it."""

import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1]


def test_bringup_starts_the_imu_always():
    t = (SRC.parent / "r2_bringup/launch/dome_tracker.launch.py").read_text(encoding="utf-8")
    block = t[t.index('package="r2_imu_bno085"'):]
    block = block[:block.index("IncludeLaunchDescription(")]      # only this Node(...), not the next one
    assert 'executable="bno085_node"' in block and "condition=" not in block
    assert '"simulate"' in block            # simulate follows sim:=true


def test_node_offers_the_services_and_status():
    t = (SRC / "r2_imu_bno085/bno085_node.py").read_text(encoding="utf-8")
    for name in ("/imu/level_here", "/imu/heading_zero", "/imu/forget_calibration", "/imu/status",
                 "add_on_set_parameters_callback", "check_setting", "save_user", "sim_sample"):
        assert name in t, name


def test_package_depends_on_std_srvs_and_yaml():
    t = (SRC / "package.xml").read_text(encoding="utf-8")
    assert "std_srvs" in t and "python3-yaml" in t
