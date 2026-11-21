# hardware

*In English: [README.md](README.md)*

Las piezas de ROS2D2 que se imprimen o se encargan. La lista completa de material (Pi, sensores,
cables...) está en [HARDWARE.md](../HARDWARE.md).

| Carpeta | Qué es |
|---|---|
| [`ros2_box_rack_v3`](ros2_box_rack_v3) | La caja rack impresa en 3D (62 × 95 × 145 mm) para la Raspberry Pi, la placa de sensores de la Pico y el conversor de 24 → 5 V: huecos para los sensores en el frente, XT60 e interruptor delante, orejas desmontables. STL, guía de impresión y montaje paso a paso (fuentes OpenSCAD y sus tests) |
| [`r2_pico_carrier`](r2_pico_carrier) | La placa de sensores (KiCad): una Raspberry Pi Pico 2 con conectores para 4 VL53L0X y 5 HC-SR04, un LED de estado por conector, una pantalla de 0,96" y el pulsador DISPLAY. Gerbers para JLCPCB y PCBWay |
| [`sensor_mounts`](sensor_mounts) | Soportes impresos para los VL53L0X y los HC-SR04 en el droide, con inclinación |
| [`lidar_mount`](lidar_mount) | Un soporte basculante para el RPLIDAR C1, colgado boca abajo |
