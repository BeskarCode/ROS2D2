# firmware

*In English: [README.md](README.md)*

El firmware de las placas propias de ROS2D2. El sketch del Mega no está aquí: es
[ShadowMD Lite](https://github.com/BeskarCode/ShadowMDLite) (o el
[Shadow MD](https://github.com/BeskarCode/SHADOW_MD_EEBEL) clásico) con `ENABLE_ROS2D2`.

| Carpeta | Qué es |
|---|---|
| [`r2_pico_sensors`](r2_pico_sensors) | La Raspberry Pi Pico 2 de la placa de sensores: lee los VL53L0X y HC-SR04, maneja los LEDs y la pantalla y habla con la Pi por USB. La consola la puede actualizar desde GitHub |
| [`r2_domecam_p4`](r2_domecam_p4) | La cámara del dome: Waveshare ESP32-P4 con una OV5647. Busca caras (o el color a seguir) ella sola y solo le dice a la Pi dónde están; vídeo cuando se le pide. ESP-IDF |
| [`r2_domecam`](r2_domecam) | La primera cámara del dome, en una ESP32-S3. **Obsoleta**: no es lo bastante potente; se queda como referencia |
