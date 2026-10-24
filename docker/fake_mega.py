"""A pretend ShadowMD Mega for the test bench, on the other end of a socat pty pair.

    python3 fake_mega.py /tmp/mega-side /tmp/mega_rx.log /tmp/mega-ctl

It speaks the autonomous-mode protocol like the firmware (ENABLE_FOOT_AUTO):
  ROS:AUTO:? / ROS:AUTO:0 answer AUTO ON / AUTO OFF <reason>
  ROS:FOOT: while the mode is off -> "ERR FOOT AUTO OFF", at most once a second
Every received line goes to the log with a timestamp.

The controller is pretend too: write one word per line to the control FIFO
  button      PS + L2 (on <-> off)
  stick       the foot stick moved (off)
  controller  the foot Nav was lost (off)
  reset       the Mega restarted (off, "AUTO OFF boot")
"""

import os
import select
import sys
import time

import serial

port, log_path, ctl_path = sys.argv[1:4]
ser = serial.Serial(port, 115200, timeout=0)
if not os.path.exists(ctl_path):
    os.mkfifo(ctl_path)
ctl = os.open(ctl_path, os.O_RDONLY | os.O_NONBLOCK)
log = open(log_path, "a", buffering=1)

auto_on = False
reason = "boot"
last_err = 0.0


def say(text):
    ser.write((text + "\n").encode("ascii"))


def state():
    say("AUTO ON" if auto_on else f"AUTO OFF {reason}")


def turn_off(why):
    global auto_on, reason
    if auto_on:
        auto_on, reason = False, why
        state()


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
    elif line.startswith("ROS:FOOT:") and not auto_on:
        if time.time() - last_err >= 1.0:
            last_err = time.time()
            say("ERR FOOT AUTO OFF")


def on_control(word):
    global auto_on, reason
    log.write(f"{time.time():.3f} # {word}\n")
    if word == "button":
        if auto_on:
            turn_off("button")
        else:
            auto_on = True
            state()
    elif word in ("stick", "controller"):
        turn_off(word)
    elif word == "reset":
        auto_on, reason = False, "boot"
        state()


say("AUTO OFF boot")
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
