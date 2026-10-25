# r2_domecam

A camera for R2's dome, sent to the Raspberry Pi over WiFi. The dome turns, so the camera
needs no cables through it: 5 V from the dome, picture by WiFi.

Two boards, both with an **OV2640**; pick yours in `config.h`:

| | XIAO ESP32S3 Sense | ESP32-CAM (AI-Thinker) |
|---|---|---|
| Speed at 640x480 | about 20-25 fps | about 10-15 fps |
| Lag | lower | higher |
| USB to flash it | built in (USB-C) | no: needs an ESP32-CAM-MB base or a USB-serial adapter |
| Antenna | external, **must** be plugged in | on the board (or external, moving a tiny resistor) |
| Arduino board | `XIAO_ESP32S3`, PSRAM `OPI PSRAM` | `AI Thinker ESP32-CAM` |

The XIAO is the better dome camera; the ESP32-CAM works and is good for trying things out.

## Flash it

1. Arduino IDE, board manager: **esp32** by Espressif, version 3.x.
2. Tools:
   - XIAO: Board **XIAO_ESP32S3**, PSRAM **OPI PSRAM** (the camera does not start without it)
   - ESP32-CAM: Board **AI Thinker ESP32-CAM** (see below how to connect it)
3. Copy `config.example.h` to `config.h`, uncomment your board and fill in your WiFi.
   `config.h` stays on your computer: it is in `.gitignore`.
4. Upload, and open the serial monitor at 115200:
   ```
   r2_domecam
   Connecting to wifi....
   Connected: http://192.168.68.120/  stream http://192.168.68.120:81/stream  (RSSI -52 dBm)
   Also http://r2-domecam1.local/
   ```

The orange LED blinks while it looks for the WiFi, is on while someone receives the
stream, and blinks fast if the camera did not start (Sense board not clicked on, or the
ribbon not latched).

### ESP32-CAM: how to flash it

It has no USB of its own:

- **Easiest: the ESP32-CAM-MB base** (the little board with a micro-USB it plugs onto).
  Plug in, pick its COM port and upload. If it does not start uploading, hold **IO0** on
  the base, press and release **RST**, release **IO0**, and upload again.
- **With a USB-serial adapter (FTDI, CP2102...) set to 5 V:** 5V→5V, GND→GND, TX→U0R,
  RX→U0T, and a wire from **IO0 to GND** while uploading. Remove that wire and press RST
  to run the sketch.
- **Power:** at least 500 mA at 5 V. With less, it resets as soon as WiFi starts
  ("Brownout detector was triggered" in the serial monitor). Weak USB ports and thin
  cables are the usual culprits.
- **The white LED (GPIO 4) is the flash:** this firmware never turns it on. The red LED
  on the back is the status light.

## Use it in ROS2D2

In the web console, **Setup → File**, add a camera:

```yaml
cam2:
  source: http://r2-domecam1.local:81/stream    # or the IP, if .local does not resolve
  yaw_deg: 30
  hfov_deg: 66          # the OV2640 lens of the Sense board sees about 66 degrees
```

then **Save and restart**. Fine-tune its direction and field of view with the sliders.

## What it serves

| Address | What |
|---|---|
| `http://r2-domecam1.local:81/stream` | MJPEG for the Pi. One viewer at a time (a second one gets "busy") |
| `http://r2-domecam1.local/` | Page with the picture and the status |
| `http://r2-domecam1.local/status` | JSON: fps, WiFi signal (RSSI), chip temperature, uptime, free memory |
| `http://r2-domecam1.local/capture` | One JPEG |
| `http://r2-domecam1.local/control?var=framesize&val=5` | Change `framesize`, `quality`, `vflip`, `hmirror` until the next reboot |

Picture sizes for `framesize`: 5 = QVGA 320x240, 8 = VGA 640x480, 9 = SVGA 800x600.

## Why it is built this way

- **Low lag first.** Lag is what made the dome overshoot in the proof of concept. The
  camera always hands over its newest picture (`CAMERA_GRAB_LATEST`), WiFi power saving is
  off, and the stream has its own server so nothing else makes it wait.
- **One viewer.** Two viewers would halve both frame rates. The Pi is the viewer; the web
  console shows the Pi's copy, with the faces drawn on it.
- **Comes back by itself.** If the WiFi or the router drops, it reconnects without anyone
  touching it.
- **Name, not IP.** `r2-domecam1.local` keeps working when the router hands out a new IP.
  For a second camera, change `CAM_HOSTNAME` to `r2-domecam2`.

## Things to watch

- `temp_c` in `/status` is only meaningful on the XIAO: the original ESP32 of the
  ESP32-CAM has no usable temperature sensor and reports a fixed value.
- The XIAO and the OV2640 get warm when streaming all the time. Check `temp_c` in
  `/status`; above about 70 °C give it some air in the dome.
- `.local` names need mDNS on the Pi (avahi, installed by the setup script). If they do
  not resolve, use the IP, and better give the camera a fixed IP in the router.
