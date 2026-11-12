<!-- ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com) -->
# r2_domecam_p4: the dome camera on an ESP32-P4

The dome camera of ROS2D2 on a **Waveshare ESP32-P4-WIFI6** board (ESP32-P4 + ESP32-C6 for the
WiFi) with an **OV5647** camera (Raspberry Pi Camera (B) Rev 2.0: 5 MP, 6 mm lens, 60.6°
diagonal, about 50° horizontal, manual focus).

It does the vision work in the dome so the Pi does not have to: it finds the **faces**, or the
**colour** of the shirt R2 follows, and sends the Pi only where they are. Video only goes out
while someone tunes the camera from the console.

It speaks to the Pi exactly like the ESP32-S3 camera (`firmware/r2_domecam`), plus the colour,
so one can replace the other.

## The board

From the Waveshare docs and schematic
(<https://docs.waveshare.com/ESP32-P4-WIFI6>,
<https://files.waveshare.com/wiki/ESP32-P4-WIFI6/ESP32-P4-WIFI6-datasheet.pdf>):

| What | Where |
|------|-------|
| WiFi | ESP32-C6-MINI-1 over SDIO: P4 GPIO18 CLK, GPIO19 CMD, GPIO14-17 D0-D3, GPIO54 C6 reset (the esp_hosted defaults) |
| Camera | 22-pin MIPI-CSI connector (Raspberry Pi 5 style), 2 lanes. SCCB (I2C) SDA GPIO7, SCL GPIO8, shared with the audio codec. No reset or power-down pin |
| Memory | 32 MB flash, 32 MB PSRAM |
| Power | USB-C (also flashing and serial console, CH343) |

The OV5647 has a 15-pin ribbon: it needs a 15-to-22-pin cable (the kit includes one).

## Settings

Copy `main/config.example.h` to `main/config.h` and fill in the WiFi password of the Pi's access
point. `config.h` is in `.gitignore`.

## Build and flash

ESP-IDF 5.5 (Waveshare recommends 5.5.4). Without installing anything, with Docker:

```
docker run --rm -v <this folder>:/project -w /project espressif/idf:v5.5.4 idf.py build
```

ESP32-P4 chips v3.x and v1.x need different builds. The default is v3.x. Check yours with
`esptool.py --chip esp32p4 chip_id` and, for a v1.x chip, build with
`idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;config/rev1.defaults" build`
(delete `sdkconfig` first when switching).

Flash with `idf.py -p COMx flash monitor`, or with esptool from the files in `build/`.

## Camera

The OV5647 runs in its 1280x960 mode with 2x2 binning (45 fps): the only mode that uses the whole
sensor, so the picture has the full field of view (about 50° wide). The 800x640 and 1920x1080 modes
crop the middle. The P4's ISP does automatic exposure and white balance; its PPA scales, turns and
mirrors the picture for each user (console video, face finder, colour finder).

| URL | What |
|-----|------|
| `http://r2-domecam1.local/` | page with the video and the status |
| `/status` | JSON: name, ip, rssi, board, sensor, sensor_mode, framesize, quality, vflip, hmirror, rotate, frames, stream_clients, uptime_s, heap, psram_free |
| `/capture` | one JPEG |
| `:81/stream` | MJPEG video, encoded only while someone watches |
| `/control?var=X&val=N` | framesize (320, 640, 800, 1280), quality (1-100), vflip, hmirror (0/1), rotate (0, 90, 180, 270), brightness, ae_level. xclk, aec2, zoom, gainceiling (ESP32-S3 only) answer 400 |

The lens focuses by hand: turn it while looking at `:81/stream` with a face at about 2 m.
