# Paquetes de ROS 2

*In English: [README.md](README.md)*

Todo lo que corre en la Raspberry Pi de dentro de R2. Cada carpeta es un paquete de ROS 2; el
servicio `r2d2` los arranca todos con un único launch (`r2_bringup`).

| Paquete | Qué hace |
|---|---|
| [`r2_bringup`](r2_bringup) | El launch que lo arranca todo, con interruptores para lo que esté enchufado |
| [`r2_camera`](r2_camera) | Las cámaras: USB o de red (la cámara del dome ESP32-P4), un nodo por cámara |
| [`r2_vision`](r2_vision) | Busca caras (YuNet en la Pi, o las que encuentra la propia cámara) y el color a seguir |
| [`r2_dome_tracker`](r2_dome_tracker) | Gira el dome hacia la cara más grande que vea cualquier cámara |
| [`r2_shadow_bridge`](r2_shadow_bridge) | El único nodo que habla con el Mega (ShadowMD) por USB |
| [`r2_imu`](r2_imu) | El giroscopio y acelerómetro MPU6050 (todavía no va en el launch principal) |
| [`r2_sensors`](r2_sensors) | Dónde va cada sensor (`sensors.yaml`), el barrido del lidar recortado a lo que R2 no tapa, su motor |
| [`r2_pico_bridge`](r2_pico_bridge) | Habla con la Pico que lee los sensores de distancia (VL53L0X, HC-SR04) |
| [`r2_nav`](r2_nav) | Los modos automáticos: ir a un punto, avanzar, patrulla, seguir un color; y la odometría |
| [`r2_sim`](r2_sim) | Una habitación, un R2 y un Mega simulados, para probarlo todo sin el droide |
| [`r2_web`](r2_web) | La consola web en el puerto 8080 |

## Cómo encajan

```
cámaras ─► r2_camera ─► r2_vision (caras) ─► r2_dome_tracker ──┐
                         └► r2_vision (color) ─► r2_nav follow ─┤
lidar ─► sllidar_ros2 ─► r2_sensors (scan_crop) ─► r2_nav ──────┤─► r2_shadow_bridge ─► Mega
Pico ─► r2_pico_bridge (/range/<nombre>) ──────► r2_nav ────────┘        (USB serie)
                        r2_web (consola) ◄──► rosbridge ◄──► todos los topics
```

El Mega sigue mandando sobre el hardware: el mando siempre gana, los pies solo se mueven con un modo
automático encendido y el dome solo con el seguimiento de caras o un modo; si la Pi deja de hablar
300 ms, el Mega los para.

## Compilar y arrancar

En la Pi, `setup/setup_r2_brain.sh` instala ROS 2 y compila este workspace en `~/r2_ws`; desde un
ordenador, `setup/deploy.sh` copia y recompila lo que haya cambiado (ver [`setup`](../../setup)). A mano:

```
cd ~/r2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch r2_bringup dome_tracker.launch.py            # o sim:=true, lidar:=sim, mega:=false...
```

Los ajustes que se editan (cámaras, sensores, modos, navegación, la placa de la Pico) se guardan
desde la consola en `~/.config/ros2d2/`, y mandan sobre el `config/` de cada paquete.
