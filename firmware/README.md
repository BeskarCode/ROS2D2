# firmware

*En castellano: [README_es.md](README_es.md)*

The firmware of ROS2D2's own boards. The Mega's sketch is not here: it is
[ShadowMD Lite](https://github.com/BeskarCode/ShadowMDLite) (or the classic
[Shadow MD](https://github.com/BeskarCode/SHADOW_MD_EEBEL)) with `ENABLE_ROS2D2`.

| Folder | What it is |
|---|---|
| [`r2_pico_sensors`](r2_pico_sensors) | The Raspberry Pi Pico 2 of the sensor board: reads the VL53L0X and HC-SR04, drives the LEDs and the display, talks to the Pi over USB. The console can update it from GitHub |
| [`r2_domecam_p4`](r2_domecam_p4) | The dome camera: Waveshare ESP32-P4 with an OV5647. Finds faces (or the colour to follow) itself and only tells the Pi where they are; video on request. ESP-IDF |
| [`r2_domecam`](r2_domecam) | The first dome camera, on an ESP32-S3. **Obsolete**: not powerful enough; kept for reference |
