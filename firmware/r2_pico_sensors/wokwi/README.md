# The firmware in Wokwi

The carrier board's display, button and LEDs in the browser, on <https://wokwi.com>, with five
simulated HC-SR04 (no Pico, no Pi).

1. `python make.py` (here). It writes `sketch.ino`, `r2_pico_sensors.h` (the sketch and its
   headers in one file, rebuilt from them each time), `diagram.json` and `libraries.txt`.
2. On wokwi.com: **New project → Raspberry Pi Pico 2 → Arduino**. Paste our `sketch.ino`,
   `diagram.json` and `libraries.txt` over the ones it opens with, and add a new file
   `r2_pico_sensors.h` (the arrow next to the file tabs → *New file...*) with ours.
3. Start the simulation. The blue button is the display's; click a sensor to slide its
   distance.

What it shows, built with `WOKWI`:

- Wokwi emulates only one core, so the display runs on core 0, between the readings.
- There is no Pi: the sketch sends itself `CFG V:2 V:3 V:4 S:10:11 S:12:13 S:14:15 S:18:19
  S:20:21` on start. Wokwi has no VL53L0X, so VL1-VL3 are *not responding* (blinking x, and
  NOT RESPONDING / CHECK CONNECTION), VL4 is *not configured* and US1-US5 measure. Any other
  `CFG` can be typed in the serial monitor, as the Pi would send it.
- The ECHO dividers are left out: Wokwi's pins take the 5 V.
