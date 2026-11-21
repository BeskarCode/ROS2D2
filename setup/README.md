# setup

*En castellano: [README_es.md](README_es.md)*

Scripts to prepare the Raspberry Pi and keep it up to date. Run on the Pi unless it says otherwise.

| File | What it is |
|---|---|
| `setup_r2_brain.sh` | **First**: turns a fresh Ubuntu Server (24.04 or 26.04, 64-bit) on a Pi 4 into R2's brain: ROS 2, the tools, this workspace built in `~/r2_ws`, the `r2d2` and `r2d2-lidar` services, the USB names. 1.5 to 2.5 hours, mostly waiting on the microSD |
| `setup_droid_wifi.sh` | Turns the Pi's built-in WiFi into R2's own network (`R2D2`, the Pi at `10.42.0.1`): the dome camera and a phone join it, so the droid works the same at home and at an event. At home, reach the Pi by cable |
| `install_wifi_channel.sh` | Once, after the WiFi: the access point picks the quietest channel (1, 6 or 11) every time it starts, and the console can show and move it. Installs `r2-wifi-channel` |
| `install_pico_toolchain.sh` | Once, as the ROS2D2 user: what the console needs to build and flash the Pico firmware itself (`arduino-cli`, about 2 GB). Installs `r2-pico-flash` with a sudoers rule for that one script |
| `install_lidar_usb.sh` | Once: lets the console unplug the lidar's USB in software and plug it back. Installs `r2-lidar-usb` |
| `deploy.sh` | **On the computer** (Git Bash): copies `ros2_ws/src` (all of it, or the packages named) to the Pi, rebuilds them and writes `~/r2_ws/VERSION` for the console. `PI=<user>@<pi> setup/deploy.sh r2_web` |
| `r2d2.service`, `r2d2-lidar.service` | The systemd services: ROS2D2 at boot (`r2_bringup`, arguments in `R2D2_ARGS`), and the lidar driver while the lidar is plugged in |
| `r2-usb-names.sh` | Fixed names for the USB serial devices: `/dev/r2-mega`, `/dev/r2-lidar`, `/dev/r2-pico` |
| `r2-wifi-channel`, `r2-pico-flash`, `r2-lidar-usb` | The small helpers the install scripts put in `/usr/local/sbin`, run by the console with sudo |
| `test/` | Tests of `r2-wifi-channel` (pytest) |

After a change to Python code, `sudo systemctl restart r2d2` (deploy.sh rebuilds, the service picks
it up on restart). The full walk-through is in the main [README](../README.md#raspberry-pi-setup).
