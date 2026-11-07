# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Text protocol of ShadowMD's USB serial port (115200 baud, one command per line).

Everything ROS sends starts with ROS:, so it stands apart from the console commands:

  ROS:FOOT:<drive>,<turn>  feet, Sabertooth units -127..127 each (the Mega clamps them to
                           its own limits). Only in autonomous mode; silent on success.
                           The Mega stops the feet if none arrives for 300 ms.
  ROS:AUTO:0               switch the autonomous mode off. Only the controller (PS + L2)
                           can switch it on.
  ROS:AUTO:?               ask for the state
  ROS:DOME:<speed>         dome speed, -127..127 (the firmware clamps it). Silent on success.
                           Only with face tracking on; stops after 300 ms without one, and the
                           dome stick always wins. DM:<speed> is the same (DomeTracker PoC).
  ROS:TRACK:0              switch face tracking off. Only the controller (PS + L2 on the dome
                           Nav) can switch it on. It has nothing to do with the autonomous mode.
  ROS:TRACK:?              ask for the state

  ROS:BIND:CLEAR          forget the combo bindings (answers "BIND CLEAR")
  ROS:BIND:<COMBO>,<mode> bind a controller combo to a mode (goto|forward|patrol|follow; none frees it);
                           answers "BIND OK <COMBO> <mode>". ROS:BIND:RESET restores the default
                           (FOOT_PS_L2 -> goto). Errors: ERR BIND FULL, ERR unknown combo/mode.

The Mega answers state changes with "AUTO ON <mode>" (plain "AUTO ON" on old firmware) or "AUTO OFF <reason>"
(reason: boot, button, stick, controller, pi), and "TRACK ON" or "TRACK OFF <reason>"
(reason: boot, button, controller, pi).

Console commands the bridge lets through from /mega/command:
  MD:<n>          MarcDuino function n, like a controller button (answers "OK ...")
  S1:<cmd>        raw command to the MarcDuino on Serial1 (dome), e.g. S1::SE01
  S3:<cmd>        raw command to Serial3 (body)
Errors come back as lines starting with "ERR".
"""

import math
import re

DOME_STOP ="ROS:DOME:0\n"
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
    """m/s and rad/s -> Sabertooth (drive, turn), limited to max_linear/max_angular first.

    NaN or infinity (a planner bug upstream) means stop, never full speed.
    """
    if not (math.isfinite(linear) and math.isfinite(angular)):
        return 0, 0
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


_AUTO_LINE = re.compile(r"AUTO (?:ON(?: ([a-z]+))?|OFF ([a-z]+))$")
_BIND_OK = re.compile(r"BIND OK ([A-Z0-9_]+) ([a-z]+)$")
_BIND_ERR = re.compile(r"ERR (BIND FULL|unknown combo|unknown mode)$")
_TRACK_LINE = re.compile(r"TRACK (ON|OFF ([a-z]+))$")


def _parse_mode_line(pattern, line):
    m = pattern.search(line.strip())
    if m is None:
        return None
    return (True, "") if m.group(1) == "ON" else (False, m.group(2))


def parse_auto_line(line):
    """"AUTO ON <mode>" -> (True, mode), plain "AUTO ON" (old firmware) -> (True, "goto"),
    "AUTO OFF <reason>" -> (False, reason), anything else -> None.

    Matched at the end of the line: the MarcDuino echo can leave a partial line in front.
    """
    m = _AUTO_LINE.search(line.strip())
    if m is None:
        return None
    if m.group(2) is not None:
        return False, m.group(2)
    return True, m.group(1) or "goto"


def bind_lines(bindings):
    """The lines that give the Mega its combo bindings: clear, then one per combo (sorted)."""
    return ["ROS:BIND:CLEAR\n"] + [f"ROS:BIND:{c},{m}\n" for c, m in sorted(bindings.items())]


def parse_bind_reply(line):
    """The Mega's answer to ROS:BIND: ("OK", combo, mode), ("CLEAR",), ("RESET",),
    ("ERR", text), or None for any other line."""
    line = line.strip()
    m = _BIND_OK.search(line)
    if m:
        return "OK", m.group(1), m.group(2)
    if line.endswith("BIND CLEAR"):
        return ("CLEAR",)
    if line.endswith("BIND RESET"):
        return ("RESET",)
    m = _BIND_ERR.search(line)
    return ("ERR", m.group(1)) if m else None


SILENT_OFF_REASONS = ("boot", "disconnected")


def auto_transition(old_mode, on, detail):
    """What an AUTO line means: (mode, reason, sound) for the new state.

    detail is the mode when on, the reason when off. mode is "" when off, reason "" when on.
    sound is None, ("sound_on", mode) when a mode switched on or changed, or
    ("sound_off", old_mode) when a mode went off for a real reason (not boot or a lost port).
    """
    mode = detail if on else ""
    reason = "" if on else detail
    if on and mode != old_mode:
        return mode, reason, ("sound_on", mode)
    if not on and old_mode and reason not in SILENT_OFF_REASONS:
        return mode, reason, ("sound_off", old_mode)
    return mode, reason, None


def lines_for_mega_line(line, bindings):
    """What to send back for a line the Mega printed: the bindings after it boots, else nothing."""
    if parse_auto_line(line) == (False, "boot"):
        return bind_lines(bindings)
    return []


def parse_track_line(line):
    """Same as parse_auto_line, for face tracking: "TRACK ON" / "TRACK OFF <reason>"."""
    return _parse_mode_line(_TRACK_LINE, line)


def is_auto_off_error(line):
    """The Mega refused a ROS:FOOT: because the mode is off: our idea of the mode is stale."""
    return line.strip() == "ERR FOOT AUTO OFF"


def command_allowed(cmd, prefixes):
    """Only commands starting with one of the allowed prefixes go through (case-insensitive)."""
    cmd = cmd.strip()
    return bool(cmd) and "\n" not in cmd and any(cmd.upper().startswith(p.upper()) for p in prefixes)


def is_error(line):
    return line.startswith("ERR")


def units_to_twist(drive_units, turn_units, drive_per_mps, turn_per_radps):
    """Sabertooth (drive, turn) -> (m/s, rad/s): the inverse of twist_to_units."""
    return drive_units / drive_per_mps, turn_units / turn_per_radps


def calibration_factor(units, measured, seconds, turning):
    """Units per m/s (measured = metres covered) or per rad/s (measured = full turns)."""
    amount = measured * 2 * math.pi if turning else measured
    return units / (amount / seconds)
