from r2_shadow_bridge.protocol import command_allowed, dome_line, dome_tick, is_error

PREFIXES = ["MD:", "S1:", "S3:"]


def test_dome_line():
    assert dome_line(25, 80) == "DM:25\n"
    assert dome_line(-40, 80) == "DM:-40\n"


def test_dome_line_is_clamped():
    assert dome_line(200, 80) == "DM:80\n"
    assert dome_line(-200, 80) == "DM:-80\n"
    assert dome_line(30, 0) == "DM:0\n"


def test_allowed_commands():
    assert command_allowed("MD:12", PREFIXES)
    assert command_allowed("s1::SE01", PREFIXES)
    assert command_allowed("  S3:#01  ", PREFIXES)


def test_rejected_commands():
    assert not command_allowed("DM:80", PREFIXES)          # the dome goes through /dome/speed_cmd
    assert not command_allowed("", PREFIXES)
    assert not command_allowed("MD:1\nDM:80", PREFIXES)   # no smuggling a second line


def test_is_error():
    assert is_error("ERR Invalid DM speed")
    assert not is_error("OK marcDuinoButtonPush(1, 12)")


def test_dome_tick_repeats_while_turning():
    assert dome_tick(True, 30, True, 80) == ("DM:30\n", False)
    assert dome_tick(True, -30, False, 80) == ("DM:-30\n", False)


def test_dome_tick_one_stop_then_silence_at_zero():
    line, stopped = dome_tick(True, 0, False, 80)        # was turning, now wants 0
    assert (line, stopped) == ("DM:0\n", True)
    assert dome_tick(True, 0, stopped, 80) == (None, True)   # still 0: say nothing


def test_dome_tick_one_stop_then_silence_when_stale():
    line, stopped = dome_tick(False, 30, False, 80)      # the tracker went quiet
    assert (line, stopped) == ("DM:0\n", True)
    assert dome_tick(False, 30, stopped, 80) == (None, True)


def test_dome_tick_speaks_again_when_turning_resumes():
    assert dome_tick(True, 25, True, 80) == ("DM:25\n", False)


def test_dome_tick_clamped_to_zero_counts_as_stop():
    assert dome_tick(True, 30, True, 0) == (None, True)
