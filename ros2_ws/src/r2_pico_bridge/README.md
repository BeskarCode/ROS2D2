# r2_pico_bridge

*En castellano: [README_es.md](README_es.md)*

The bridge to the Raspberry Pi Pico that reads the distance sensors (VL53L0X and HC-SR04) on the
ROS2D2 sensor board (`firmware/r2_pico_sensors`, `hardware/r2_pico_carrier`), on `/dev/r2-pico`.

It sends the Pico the sensors and pins of `sensors.yaml` (again every time it is saved from the
console) and publishes what each one reads:

| Topic | Type | |
|---|---|---|
| `/range/<name>` | `sensor_msgs/Range` | each sensor that answers; `inf` = nothing in range. One that does not answer publishes nothing, so whoever listens sees it go quiet (never "the way is clear") |
| `/pico/connected` | `std_msgs/Bool` | latched |
| `/pico/state` | `std_msgs/String` | JSON every second and on change: firmware, each sensor's state, the display, the telemetry; the console reads it |
| `/pico/command` | `std_msgs/String` | in: board commands from the console (display on/off, identify a connector, `BOOT` to flash) |
| `/pico/telemetry_request`, `/pico/mirror_request` | `std_msgs/Bool` | in: the console asks for the telemetry and the live copy of the board while System is open |
| `/pico/mirror` | `std_msgs/String` | out: the board's LEDs and display, for the copy in Setup → System |
| `/pico/release` | `std_srvs/SetBool` | service: let go of the port (to flash the Pico) and take it back |

The board's own settings (display timeout, brightness, LEDs, power saving) are in
`config/pico_board.yaml`, edited in Setup → System → Pico board → Settings.

`fake_pico` pretends to be the board, for the test bench without one.
