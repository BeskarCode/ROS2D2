# r2_pico_sensors

A Raspberry Pi **Pico 2** (RP2350) that reads R2's distance sensors (VL53L0X ToF and
HC-SR04 ultrasonic) and sends the readings to the Pi 4 over USB. The Pico only measures:
stopping the feet is the Pi's job.

The Pico has no pins built in. The Pi sends it the sensors and their pins from
`sensors.yaml` (Setup → Sensors in the web console), so moving a sensor to another pin
needs no new firmware: change it in the console, save, and move the wire.

## Try it in the browser

The display, the button, the LEDs and the HC-SR04 sensors run in [Wokwi](https://wokwi.com), with a slider to change each sensor's distance. Press play (the first build can wait 2-3 minutes in the free queue):

[![ROS2D2 Pico sensors display on Wokwi](https://thumbs.wokwi.com/projects/479319770579184641/thumbnail.jpg?tile&dark=1)](https://wokwi.com/projects/479319770579184641)

## Wiring

![Wiring](wiring.svg)

`wiring.svg` opens in any browser and prints on A4 landscape (`python wiring.py wiring.svg`
draws it again). With today's `sensors.yaml`:

| Sensor | Type | Pico pin | GPIO | Wire |
|---|---|---|---|---|
| all VL53L0X | VIN | 36 `3V3(OUT)` | — | red |
| all HC-SR04 | VCC | 40 `VBUS` (5 V) | — | orange |
| all | GND | 38 (or any GND) | — | black |
| all VL53L0X | SDA | 21 | GP16 | blue |
| all VL53L0X | SCL | 22 | GP17 | green |
| tof_front_left | XSHUT | 4 | GP2 | purple |
| tof_front | XSHUT | 5 | GP3 | purple |
| tof_front_right | XSHUT | 6 | GP4 | purple |
| tof_floor | XSHUT | 7 | GP5 | purple |
| sonar_front_left | TRIG / ECHO | 14 / 15 | GP10 / GP11 | yellow / teal |
| sonar_front_right | TRIG / ECHO | 16 / 17 | GP12 / GP13 | yellow / teal |
| sonar_rear | TRIG / ECHO | 19 / 20 | GP14 / GP15 | yellow / teal |

- **The HC-SR04's ECHO is 5 V; the Pico takes 3.3 V.** Always through a divider: ECHO →
  1 kΩ → Pico pin, and Pico pin → 2 kΩ → GND (or a level shifter). Without it the pin dies.
  TRIG goes straight (3.3 V triggers it).
- VBUS is 5 V only while the Pico is powered by USB (it is: from the Pi).
- About 20 mA per VL53L0X and 15 mA per HC-SR04: all seven fit on the Pi's USB.
- Wired straight to the Pico, keep the I2C wires (SDA/SCL) short, under 50 cm (on the carrier board
  every VL connector sits behind its I2C repeater and takes up to 1 m). The VL53L0X's GPIO1 is not used.
- **Reserved, never for a sensor:** GP16 and GP17 (I2C); GP0, GP1, GP6-GP9, GP22, GP27 and
  GP28 (the carrier board's status LEDs) and GP26 (its button); GP23, GP24, GP25 (the Pico's own: GP25 is the LED). The console does not
  offer them.

## The carrier board

`hardware/r2_pico_carrier` is a board to order assembled: the Pico plugs in, and each sensor
has its own connector (VL1-VL4, US1-US5), the ECHO dividers are on it, and it adds a 5 V input,
one status LED per connector, each on its own GPIO (VL1-VL4 = GP28, GP27, GP22, GP9;
US1-US5 = GP0, GP1, GP6, GP7, GP8), and an OLED display with a button (GP26). The firmware
handles them on the RP2350's second core; without the board, nothing changes. Those GPIOs are
therefore reserved too, which leaves GP2-5, GP10-15 and GP18-21 for sensors. See its README.

The display: off until the button is pressed; then the logo; the next press every sensor at
once, one bar each (taller the nearer the obstacle); then each press one connector, VL1 to US5,
and after US5 every sensor again. Held for 3 s, or 30 s without a press: off. `wokwi/` runs it in the browser
([online demo](https://wokwi.com/projects/479319770579184641); see its README).

## LED

- Slow blink (once a second): running, but the Pi has not sent the sensors yet.
- On, off for a moment once a second (with the heartbeat): measuring. On without the blink: running, but no sensor answers.

## Build and flash

Once, on the computer: `arduino-cli` with the Pico core and the VL53L0X library:

```
arduino-cli config add board_manager.additional_urls https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
arduino-cli core update-index
arduino-cli core install rp2040:rp2040
arduino-cli lib install VL53L0X
arduino-cli lib install "Adafruit GFX Library"
```

On the Pi, `setup/install_pico_toolchain.sh` installs all this (and what the web console needs to
check GitHub for new firmware and flash it from Setup -> System) in one go.

The first time, the Pico has no firmware: hold BOOTSEL while plugging it into the Pi. It
shows up as a USB drive labelled `RP2350`; copy `build/r2_pico_sensors.ino.uf2` onto it.

From then on, from Git Bash on the computer:

```
PI=<your-user>@<pi-address> firmware/r2_pico_sensors/flash.sh
```

It builds (`build.sh`), copies the `.uf2` to the Pi, stops the `r2d2` service, restarts the
Pico into its USB loader (1200 baud on `/dev/r2-pico`), copies the file and starts the service
again. No BOOTSEL.

`build.sh` builds with the git commit of this folder in the firmware (`-dirty` if it has
changes not committed); the Pico says it in its `HELLO` answer and the console shows it.
`build.sh --jobs 2 --nice` builds gently (on the Pi, while R2 runs).

Flashing 0.2.0 from a PC before the Pi has the new ROS2D2: it works, but the Pi's older bridge
shows the firmware commit as unknown and ignores the telemetry and display lines until it is
updated (`setup/deploy.sh`).

Host tests (plain C++, any computer with g++), from this folder:
`for t in test/*.cpp; do g++ -std=c++17 -Wall -I. $t -o /tmp/t && /tmp/t; done`.

## Protocol (USB serial, one line each, ASCII)

Pi → Pico:

| Line | Answer |
|---|---|
| `HELLO` | `PICO r2_pico_sensors <fw> proto 3 commit <git commit>` (0.2.0: `proto 2`; before 0.2.0: `proto 1`, no commit) |
| `CFG` + up to 12 items: `V:<xshut>` (VL53L0X) or `S:<trig>:<echo>` (HC-SR04); a sensor's index is its place in the line; `CFG` alone = none | `CFG OK <n>` or `CFG ERR <why>` (`bad item <k>`, `pin <p> reserved`, `pin <p> twice`, `too many`). After an error the Pico has no sensors until the next good `CFG`. |
| `BOOT` | none: the Pico restarts into its USB loader (for flashing) |
| `TM 1` / `TM 0` | `TM OK`: telemetry on / off (off after a restart). The Pi asks for it only while the console's System tab shows it. |
| `UI t=<s> b=<0-3> led=<auto\|on\|conn\|off\|err>` | `UI OK` or `UI ERR <why>`: the display's timeout (10, 30, 60, 300 s; 0 = never), brightness and the status LEDs' mode (auto = only with the display on, on, conn = only those measuring, off, err = only those not responding). Any of them, any order. The Pico keeps none: the Pi (`pico_board.yaml`) sends them after every `CFG`. |
| `DISP on [all\|VL1..US5]` / `DISP off` | `DISP OK`: the display on (every sensor, or one) or off, now |
| `ID <VL1..US5>` | `ID OK`: that connector's LED blinks at 5 Hz for 5 s, whatever the LED mode |
| `MIR 1` / `MIR 0` | `MIR OK`: the board mirror for the console's System tab on / off (0.3.0). Off on its own 5 s after the last `MIR 1`; the Pi renews it every 2 s while the tab is open. |
| `PRESS short` / `PRESS long` | `PRESS OK` (or `PRESS ERR bad press`): the DISPLAY button pressed from the console, the same as a press of the real one / holding it 3 s (0.3.0) |
| `DBG` | for each VL53L0X that answers: `DBG <index> addr=.. irq=.. rs=..(st..) raw=.. seq=.. mode=.. lim=.. vcsel=.. budget=.. i2c=.. fails=..` (its raw result and settings; `seq=e8` and `budget=33823` when healthy), then `DBG end` |
| anything else | `ERR unknown` (a line over 200 characters: `ERR too long`) |

Pico → Pi:

| Line | When |
|---|---|
| `HB <ms> <states>` | every second. `<states>` is `-` with no `CFG` yet, else one letter per sensor: `O` answers, `N` not answering. E.g. `HB 12034 NNNNNNN`. |
| `R <i>:<mm> <i>:<mm> …` | every 50 ms, the sensors with a new reading since the last `R`. `-1` = answers, nothing in range. |
| `DS <off\|logo\|all\|VL1..US5>` | what the display shows, when it changes and after `HELLO` (the console's buttons follow it) |
| `LED <10 digits 0/1>` | with `MIR 1`: each connector LED's level, VL1..US5, then the Pico's own green LED, when one changes and every second |
| `FB <base64>` / `FB off` | with `MIR 1`: the display's picture (the 8 SSD1306 pages, 1024 bytes: a byte per column, LSB on top) when it changed, at most every 200 ms; `FB off` once when it goes off |
| `BTN short` / `BTN long` | with `MIR 1`: the real button was pressed / held until the display went off |
| `T c0=<%> c1=<%> bus=<%> disp=<%> wait=<ms> temp=<tenths °C> up=<s> rps=<n>,<n>,…` | with `TM 1`, every second after `HB`: each core's load (loop turns of 20 µs or more, without their waits for the bus), the I2C bus held and the part held by the display, the longest a VL53L0X waited for the bus, the chip's temperature, seconds up, readings per second of each sensor. |

The Pi (`r2_pico_bridge`) sends `HELLO` and `CFG` when it opens the port, and `CFG` again
when a `HB` shows `-` or a different number of sensors, or when `sensors.yaml` changes.
A sensor that does not answer is retried every 2 s, so one plugged in later shows up alone.
