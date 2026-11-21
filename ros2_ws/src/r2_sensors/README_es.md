# r2_sensors

*In English: [README.md](README.md)*

Los sensores del droide tal como los ve ROS: dónde va cada uno, el barrido del lidar y su motor. Todo
sale de `sensors.yaml` (`config/`, o `~/.config/ros2d2/` en cuanto se guarda desde Setup → Sensors):
el tipo de cada sensor, su posición, hacia dónde mira, su campo de visión, su alcance y si está en uso.

| Nodo | Qué hace |
|---|---|
| `sensor_tf` | La posición de cada sensor en `/tf_static` (`base_link` → `<nombre>_link`); al guardar el fichero se mueven en un segundo |
| `scan_crop` | `/scan_raw` → `/scan` sin los rayos que tapa el propio cuerpo de R2 (el lidar va en el pie delantero y solo ve hacia delante). Los sectores ciegos puestos en la consola los aplica el driver del lidar |
| `lidar_motor` | Hace girar el motor del lidar como dice `sensors.yaml`: `always`, `with_modes` (solo con un modo encendido) u `off` |
| `fake_lidar` | Un lidar de mentira (`lidar:=sim`): una habitación pequeña con una pata de silla, vista desde donde va el lidar |

```
ros2 launch r2_sensors sensors.launch.py
ros2 launch r2_sensors lidar_driver.launch.py     # el RPLIDAR C1 (sllidar_ros2); lo arranca el servicio r2d2-lidar
```

El driver del lidar es un fork de `sllidar_ros2` que además publica la información del lidar
(`/lidar/info`) y recibe el motor y el modo de barrido desde la consola. `config.py` lee y comprueba
`sensors.yaml` (probado con pytest); la consola usa las mismas reglas.
