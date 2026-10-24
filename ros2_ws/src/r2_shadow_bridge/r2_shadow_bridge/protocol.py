"""Text protocol of ShadowMD's USB serial port (115200 baud, one command per line).

Everything ROS sends starts with ROS:, so it stands apart from the console commands:

  ROS:FOOT:<drive>,<turn>  feet, Sabertooth units -127..127 each (the Mega clamps them to
                           its own limits). Only in autonomous mode; silent on success.
                           The Mega stops the feet if none arrives for 300 ms.
  ROS:AUTO:0               switch the autonomous mode off. Only the controller (PS + L2)
                           can switch it on.
  ROS:AUTO:?               ask for the state
  ROS:DOME:<speed>         dome speed, -127..127 (the firmware clamps it). Silent on success.
                           Only in autonomous mode; stops after 300 ms without one, and the
                           dome stick always wins. DM:<speed> is the same (DomeTracker PoC).

The Mega answers state changes with "AUTO ON" or "AUTO OFF <reason>"
(reason: boot, button, stick, controller, pi).

Console commands the bridge lets through from /mega/command:
  MD:<n>          MarcDuino function n, like a controller button (answers "OK ...")
  S1:<cmd>        raw command to the MarcDuino on Serial1 (dome), e.g. S1::SE01
  S3:<cmd>        raw command to Serial3 (body)
Errors come back as lines starting with "ERR".
"""

DOME_STOP = "ROS:DOME:0\n"
FOOT_STOP = "ROS:FOOT:0,0\n"


def _clamp(value, limit):
    return max(-limit, min(limit, value))


def dome_line(speed, max_speed):
    """ROS:DOME: line for a speed, clamped to +-max_speed."""
    return f"ROS:DOME:{_clamp(int(speed), max_speed)}\n"


def dome_tick(fresh, speed, stopped, max_speed):
    """What to send to the Mega on one bridge tick: (line or None, stopped).

    While the dome turns, repeat ROS:DOME: so the Mega's 300 ms timeout never fires.
    When it should stand still (speed 0, or the dome command went stale), send a single
    stop and then nothing: the dome is already stopped and the controller stays free.
    """
    line = dome_line(speed, max_speed)
    if fresh and line != DOME_STOP:
        return line, False
    if not stopped:
        return DOME_STOP, True
    return None, True


def foot_line(drive, turn):
    return f"ROS:FOOT:{int(drive)},{int(turn)}\n"


def twist_to_units(linear, angular, drive_per_mps, turn_per_radps, max_linear, max_angular):
    """m/s and rad/s -> Sabertooth (drive, turn), limited to max_linear/max_angular first."""
    drive = round(_clamp(linear, max_linear) * drive_per_mps)
    turn = round(_clamp(angular, max_angular) * turn_per_radps)
    return _clamp(int(drive), 127), _clamp(int(turn), 127)


def foot_tick(fresh, auto_on, drive, turn, stopped):
    """What to send for the feet on one bridge tick: (line or None, stopped).

    Same idea as dome_tick. With the autonomous mode off nothing is sent at all, not even
    a stop: the Mega has already stopped the feet and would only answer ERR.
    """
    if not auto_on:
        return None, True
    if fresh and (drive, turn) != (0, 0):
        return foot_line(drive, turn), False
    if not stopped:
        return FOOT_STOP, True
    return None, True


def parse_auto_line(line):
    """"AUTO ON" -> (True, ""), "AUTO OFF <reason>" -> (False, reason), anything else -> None."""
    words = line.split()
    if words == ["AUTO", "ON"]:
        return True, ""
    if len(words) == 3 and words[:2] == ["AUTO", "OFF"]:
        return False, words[2]
    return None


def command_allowed(cmd, prefixes):
    """Only commands starting with one of the allowed prefixes go through (case-insensitive)."""
    cmd = cmd.strip()
    return bool(cmd) and "\n" not in cmd and any(cmd.upper().startswith(p.upper()) for p in prefixes)


def is_error(line):
    return line.startswith("ERR")
