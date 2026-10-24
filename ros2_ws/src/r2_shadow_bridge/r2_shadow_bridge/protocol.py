"""Text protocol of ShadowMD's USB serial port (115200 baud, one command per line).

  DM:<speed>      dome speed, -127..127 (the firmware clamps it). Silent on success.
                  The Mega stops the dome if no DM: arrives for 300 ms, and its
                  controller always wins over DM: (needs ENABLE_DOME_TRACKER).
  MD:<n>          MarcDuino function n, like a controller button (answers "OK ...")
  S1:<cmd>        raw command to the MarcDuino on Serial1 (dome), e.g. S1::SE01
  S3:<cmd>        raw command to Serial3 (body)
Errors come back as lines starting with "ERR".
"""


def dome_line(speed, max_speed):
    """DM: line for a speed, clamped to +-max_speed."""
    speed = max(-max_speed, min(max_speed, int(speed)))
    return f"DM:{speed}\n"


def dome_tick(fresh, speed, stopped, max_speed):
    """What to send to the Mega on one bridge tick: (line or None, stopped).

    While the dome turns, repeat DM: so the Mega's 300 ms timeout never fires. When
    it should stand still (speed 0, or the dome command went stale), send a single
    DM:0 and then nothing: the dome is already stopped and the controller stays free.
    """
    line = dome_line(speed, max_speed)
    if fresh and line != "DM:0\n":
        return line, False
    if not stopped:
        return "DM:0\n", True
    return None, True


def command_allowed(cmd, prefixes):
    """Only commands starting with one of the allowed prefixes go through (case-insensitive)."""
    cmd = cmd.strip()
    return bool(cmd) and "\n" not in cmd and any(cmd.upper().startswith(p.upper()) for p in prefixes)


def is_error(line):
    return line.startswith("ERR")
