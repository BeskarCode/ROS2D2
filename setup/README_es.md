# setup

*In English: [README.md](README.md)*

Scripts para preparar la Raspberry Pi y tenerla al día. Se ejecutan en la Pi, salvo que se diga otra cosa.

| Fichero | Qué es |
|---|---|
| `setup_r2_brain.sh` | **Lo primero**: convierte un Ubuntu Server recién instalado (24.04 o 26.04, 64 bits) en una Pi 4 en el cerebro de R2: ROS 2, las herramientas, este workspace compilado en `~/r2_ws`, los servicios `r2d2` y `r2d2-lidar` y los nombres USB. De 1,5 a 2,5 horas, casi todo esperando a la microSD |
| `setup_droid_wifi.sh` | Convierte la WiFi de la Pi en la red propia de R2 (`R2D2`, la Pi en `10.42.0.1`): se conectan la cámara del dome y un móvil, así el droide funciona igual en casa que en un evento. En casa, a la Pi se llega por cable |
| `install_wifi_channel.sh` | Una vez, después de la WiFi: el punto de acceso elige el canal más tranquilo (1, 6 u 11) cada vez que arranca, y la consola puede enseñarlo y cambiarlo. Instala `r2-wifi-channel` |
| `install_pico_toolchain.sh` | Una vez, como el usuario de ROS2D2: lo que necesita la consola para compilar y grabar ella misma el firmware de la Pico (`arduino-cli`, unos 2 GB). Instala `r2-pico-flash` con una regla de sudoers solo para ese script |
| `install_lidar_usb.sh` | Una vez: deja que la consola desenchufe por software el USB del lidar y lo vuelva a enchufar. Instala `r2-lidar-usb` |
| `deploy.sh` | **En el ordenador** (Git Bash): copia `ros2_ws/src` (entero o los paquetes que digas) a la Pi, los recompila y escribe `~/r2_ws/VERSION` para la consola. `PI=<usuario>@<pi> setup/deploy.sh r2_web` |
| `r2d2.service`, `r2d2-lidar.service` | Los servicios de systemd: ROS2D2 al arrancar (`r2_bringup`, argumentos en `R2D2_ARGS`) y el driver del lidar mientras el lidar está enchufado |
| `r2-usb-names.sh` | Nombres fijos para los dispositivos serie USB: `/dev/r2-mega`, `/dev/r2-lidar`, `/dev/r2-pico` |
| `r2-wifi-channel`, `r2-pico-flash`, `r2-lidar-usb` | Las pequeñas herramientas que los scripts de instalación dejan en `/usr/local/sbin`, y que la consola ejecuta con sudo |
| `test/` | Tests de `r2-wifi-channel` (pytest) |

Tras cambiar código Python, `sudo systemctl restart r2d2` (deploy.sh recompila, el servicio lo coge al
reiniciar). El paso a paso completo está en el [README](../README.md#raspberry-pi-setup) principal.
