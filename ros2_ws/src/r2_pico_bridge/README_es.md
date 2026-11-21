# r2_pico_bridge

*In English: [README.md](README.md)*

El puente con la Raspberry Pi Pico que lee los sensores de distancia (VL53L0X y HC-SR04) en la placa de
sensores de ROS2D2 (`firmware/r2_pico_sensors`, `hardware/r2_pico_carrier`), en `/dev/r2-pico`.

Le manda a la Pico los sensores y pines de `sensors.yaml` (otra vez cada vez que se guarda desde la
consola) y publica lo que lee cada uno:

| Topic | Tipo | |
|---|---|---|
| `/range/<nombre>` | `sensor_msgs/Range` | cada sensor que contesta; `inf` = nada a su alcance. Uno que no contesta no publica nada, así que quien escucha lo ve callarse (nunca "el camino está libre") |
| `/pico/connected` | `std_msgs/Bool` | latched |
| `/pico/state` | `std_msgs/String` | JSON cada segundo y en cada cambio: firmware, estado de cada sensor, la pantalla, la telemetría; lo lee la consola |
| `/pico/command` | `std_msgs/String` | entra: órdenes a la placa desde la consola (pantalla, identificar un conector, `BOOT` para grabarla) |
| `/pico/telemetry_request`, `/pico/mirror_request` | `std_msgs/Bool` | entra: la consola pide la telemetría y la copia en directo de la placa mientras System está abierta |
| `/pico/mirror` | `std_msgs/String` | sale: los LEDs y la pantalla de la placa, para la copia de Setup → System |
| `/pico/release` | `std_srvs/SetBool` | servicio: soltar el puerto (para grabar la Pico) y volver a cogerlo |

Los ajustes de la propia placa (apagado de la pantalla, brillo, LEDs, ahorro de energía) están en
`config/pico_board.yaml`, y se editan en Setup → System → Pico board → Settings.

`fake_pico` hace de placa, para el banco de pruebas sin ella.
