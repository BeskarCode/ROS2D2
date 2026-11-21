# hardware

*En castellano: [README_es.md](README_es.md)*

The parts of ROS2D2 you print or order. The full parts list (Pi, sensors, cables...) is in
[HARDWARE.md](../HARDWARE.md).

| Folder | What it is |
|---|---|
| [`ros2_box_rack_v3`](ros2_box_rack_v3) | The 3D-printed rack box (62 × 95 × 145 mm) for the Raspberry Pi, the Pico sensor board and the 24 → 5 V converter: sensor bays in its face, XT60 and switch on the front, removable ears. STL, print guide and step-by-step assembly (OpenSCAD sources and their tests) |
| [`r2_pico_carrier`](r2_pico_carrier) | The sensor board (KiCad): a Raspberry Pi Pico 2 with connectors for 4 VL53L0X and 5 HC-SR04, a status LED per connector, a 0.96" display and the DISPLAY button. Gerbers for JLCPCB and PCBWay |
| [`sensor_mounts`](sensor_mounts) | Printed mounts for the VL53L0X and the HC-SR04 on the droid, with tilt |
| [`lidar_mount`](lidar_mount) | A tilting mount for the RPLIDAR C1, hanging upside down |
