"""A pretend ShadowMD Mega for the test bench, on the other end of a socat pty pair.

    ros2 run r2_sim fake_mega /tmp/mega-side /tmp/mega_rx.log /tmp/mega-ctl

It speaks the autonomous-mode and face-tracking protocol like the firmware (ENABLE_ROS2D2):
  ROS:AUTO:? / ROS:AUTO:0 answer AUTO ON / AUTO OFF <reason>
  ROS:TRACK:? / ROS:TRACK:0 answer TRACK ON / TRACK OFF <reason>
  ROS:FOOT: while the mode is off -> "ERR FOOT AUTO OFF", at most once a second
Every received line goes to the log with a timestamp.

The controllers are pretend too: write one word per line to the control FIFO
  button           PS + L2 on the foot Nav (autonomous mode on <-> off)
  stick            the foot stick moved (autonomous mode off)
  controller       the foot Nav was lost (autonomous mode off)
  dome_button      PS + L2 on the dome Nav (face tracking on <-> off)
  dome_stick       the dome stick moved (face tracking stays on: it only pauses)
  dome_controller  the dome Nav was lost (face tracking off)
  reset            the Mega restarted (both off, "AUTO OFF boot" and "TRACK OFF boot")
  glitch           the stick, with the AUTO line glued to a MarcDuino echo
  silent           off, and the AUTO line is lost
"""

import os
import select
import sys
import time

import serial

ser = log = None
auto_on = False
reason = "boot"
track_on = False
track_reason = "boot"
last_err = 0.0


def say(text):
    ser.write((text + "\n").encode("ascii"))


def state():
    say("AUTO ON" if auto_on else f"AUTO OFF {reason}")


def track_state():
    say("TRACK ON" if track_on else f"TRACK OFF {track_reason}")


def turn_off(why):
    global auto_on, reason
    if auto_on:
        auto_on, reason = False, why
        state()


def track_off(why):
    global track_on, track_reason
    if track_on:
        track_on, track_reason = False, why
        track_state()


def on_line(line):
    global last_err
    log.write(f"{time.time():.3f} {line}\n")
    if line == "ROS:AUTO:?":
        state()
    elif line == "ROS:AUTO:0":
        if auto_on:
            turn_off("pi")
        else:
            state()
    elif line.startswith("ROS:AUTO:"):
        say("ERR ROS:AUTO only 0 or ?")
    elif line == "ROS:TRACK:?":
        track_state()
    elif line == "ROS:TRACK:0":
        if track_on:
            track_off("pi")
        else:
            track_state()
    elif line.startswith("ROS:TRACK:"):
        say("ERR ROS:TRACK only 0 or ?")
    elif line.startswith("ROS:FOOT:") and not auto_on:
        if time.time() - last_err >= 1.0:
            last_err = time.time()
            say("ERR FOOT AUTO OFF")


def on_control(word):
    global auto_on, reason, track_on, track_reason
    log.write(f"{time.time():.3f} # {word}\n")
    if word == "button":
        if auto_on:
            turn_off("button")
        else:
            auto_on = True
            state()
    elif word in ("stick", "controller"):
        turn_off(word)
    elif word == "dome_button":
        if track_on:
            track_off("button")
        else:
            track_on = True
            track_state()
    elif word == "dome_stick":   # only pauses the tracker on the real Mega: no state change
        pass
    elif word == "dome_controller":
        track_off("controller")
    elif word == "reset":
        auto_on, reason = False, "boot"
        track_on, track_reason = False, "boot"
        state()
        track_state()
    elif word == "glitch":       # the stick, with the AUTO line glued to a MarcDuino echo
        if auto_on:
            auto_on, reason = False, "stick"
            ser.write(b"[MD] *ON00AUTO OFF stick\n")
    elif word == "silent":       # off, and the AUTO line is lost altogether
        auto_on, reason = False, "stick"


def main(argv=None):
    """fake_mega <port> <log> <control FIFO>: answers on <port> like the ShadowMD Mega."""
    global ser, log
    port, log_path, ctl_path = (argv or sys.argv[1:])[:3]
    ser = serial.Serial(port, 115200, timeout=0)
    if not os.path.exists(ctl_path):
        os.mkfifo(ctl_path)
    ctl = os.open(ctl_path, os.O_RDONLY | os.O_NONBLOCK)
    log = open(log_path, "a", buffering=1)
    say("AUTO OFF boot")
    say("TRACK OFF boot")
    buf = b""
    ctl_buf = b""
    while True:
        ready, _, _ = select.select([ser.fileno(), ctl], [], [], 1.0)
        if ser.fileno() in ready:
            buf += ser.read(256)
            *lines, buf = buf.replace(b"\r", b"\n").split(b"\n")
            for raw in lines:
                if raw.strip():
                    on_line(raw.decode("ascii", "replace").strip())
        if ctl in ready:
            data = os.read(ctl, 256)
            if not data:                     # writer closed: reopen so the next echo works
                os.close(ctl)
                ctl = os.open(ctl_path, os.O_RDONLY | os.O_NONBLOCK)
                continue
            ctl_buf += data
            *words, ctl_buf = ctl_buf.split(b"\n")
            for w in words:
                if w.strip():
                    on_control(w.decode().strip())


if __name__ == "__main__":
    main()
