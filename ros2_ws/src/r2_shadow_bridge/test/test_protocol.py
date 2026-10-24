from r2_shadow_bridge.protocol import (command_allowed, dome_line, dome_tick, foot_line, foot_tick,
                                       is_error, parse_auto_line, twist_to_units, units_to_twist,
                                       calibration_factor)

PREFIXES = ["MD:", "S1:", "S3:"]


def test_dome_line():
    assert dome_line(25, 80) == "ROS:DOME:25\n"
    assert dome_line(-40, 80) == "ROS:DOME:-40\n"


def test_dome_line_is_clamped():
    assert dome_line(200, 80) == "ROS:DOME:80\n"
    assert dome_line(-200, 80) == "ROS:DOME:-80\n"
    assert dome_line(30, 0) == "ROS:DOME:0\n"


def test_allowed_commands():
    assert command_allowed("MD:12", PREFIXES)
    assert command_allowed("s1::SE01", PREFIXES)
    assert command_allowed("  S3:#01  ", PREFIXES)


def test_rejected_commands():
    assert not command_allowed("DM:80", PREFIXES)          # the dome goes through /dome/speed_cmd
    assert not command_allowed("ROS:FOOT:40,0", PREFIXES)  # and the feet through /foot/cmd_vel
    assert not command_allowed("", PREFIXES)
    assert not command_allowed("MD:1\nDM:80", PREFIXES)   # no smuggling a second line


def test_is_error():
    assert is_error("ERR Invalid DM speed")
    assert not is_error("OK marcDuinoButtonPush(1, 12)")


def test_dome_tick_repeats_while_turning():
    assert dome_tick(True, 30, True, 80) == ("ROS:DOME:30\n", False)
    assert dome_tick(True, -30, False, 80) == ("ROS:DOME:-30\n", False)


def test_dome_tick_one_stop_then_silence_at_zero():
    line, stopped = dome_tick(True, 0, False, 80)        # was turning, now wants 0
    assert (line, stopped) == ("ROS:DOME:0\n", True)
    assert dome_tick(True, 0, stopped, 80) == (None, True)   # still 0: say nothing


def test_dome_tick_one_stop_then_silence_when_stale():
    line, stopped = dome_tick(False, 30, False, 80)      # the tracker went quiet
    assert (line, stopped) == ("ROS:DOME:0\n", True)
    assert dome_tick(False, 30, stopped, 80) == (None, True)


def test_dome_tick_speaks_again_when_turning_resumes():
    assert dome_tick(True, 25, True, 80) == ("ROS:DOME:25\n", False)


def test_dome_tick_clamped_to_zero_counts_as_stop():
    assert dome_tick(True, 30, True, 0) == (None, True)


def test_dome_line_uses_ros_prefix():
    assert dome_line(10, 80).startswith("ROS:DOME:")


def test_foot_line():
    assert foot_line(20, -5) == "ROS:FOOT:20,-5\n"


def test_twist_to_units_scales_and_rounds():
    assert twist_to_units(0.4, 0.0, 50, 30, 0.4, 0.6) == (20, 0)
    assert twist_to_units(0.11, -0.5, 50, 30, 0.4, 0.6) == (6, -15)


def test_twist_to_units_clamps_to_max_speed():
    assert twist_to_units(2.0, -3.0, 50, 30, 0.4, 0.6) == twist_to_units(0.4, -0.6, 50, 30, 0.4, 0.6)


def test_twist_to_units_clamps_to_127():
    assert twist_to_units(5.0, 5.0, 1000, 1000, 10, 10) == (127, 127)


def test_foot_tick_sends_while_moving():
    assert foot_tick(True, True, 20, -5, True) == ("ROS:FOOT:20,-5\n", False)


def test_foot_tick_one_stop_then_silence():
    line, stopped = foot_tick(False, True, 20, 0, False)      # cmd_vel went quiet
    assert (line, stopped) == ("ROS:FOOT:0,0\n", True)
    assert foot_tick(False, True, 20, 0, stopped) == (None, True)
    line, stopped = foot_tick(True, True, 0, 0, False)        # asked for 0
    assert (line, stopped) == ("ROS:FOOT:0,0\n", True)


def test_foot_tick_silent_when_auto_off():
    assert foot_tick(True, False, 20, 0, False) == (None, True)


def test_parse_auto_lines():
    assert parse_auto_line("AUTO ON") == (True, "")
    assert parse_auto_line("AUTO OFF boot") == (False, "boot")
    assert parse_auto_line("AUTO OFF stick") == (False, "stick")
    assert parse_auto_line("OK forwarded to Serial1") is None
    assert parse_auto_line("AUTO MAYBE") is None
    assert parse_auto_line("AUTO OFF") is None


def test_units_to_twist_inverts_twist_to_units():
    assert units_to_twist(20, 15, 50, 30) == (0.4, 0.5)
    assert twist_to_units(0.4, 0.5, 50, 30, 0.4, 0.6) == (20, 15)


def test_calibration_factor_drive():
    # 20 units for 3 s covered 1.2 m -> 0.4 m/s -> 50 units per m/s
    assert abs(calibration_factor(20, 1.2, 3.0, turning=False) - 50.0) < 1e-9


def test_calibration_factor_turn():
    # 15 units for 4 s made one full turn -> pi/2 rad/s -> 15 / (pi/2) units per rad/s
    assert abs(calibration_factor(15, 1.0, 4.0, turning=True) - 9.549) < 0.001
