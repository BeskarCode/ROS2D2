# r2_bringup

*In English: [README.md](README.md)*

El launch que arranca ROS2D2: el que ejecuta el servicio `r2d2` al encender.

```
ros2 launch r2_bringup dome_tracker.launch.py
```

Arranca las cámaras (`r2_camera`), sus buscadores de caras (`r2_vision`), el marcador de color, el
seguimiento del dome, el puente con el Mega, los sensores y el recorte del lidar (`r2_sensors`), el
puente con la Pico, los modos automáticos (`r2_nav`) y la consola web (`r2_web`). El driver del
lidar va en su propio servicio, `r2d2-lidar`, que arranca al enchufar el lidar.

| Argumento | Por defecto | Qué hace |
|---|---|---|
| `port` | `/dev/r2-mega` | El puerto serie del Mega |
| `mega` | `true` | `false`: sin puente con el Mega (no hay Mega enchufado); el seguimiento del dome simula entonces el giro del dome |
| `web` | `true` | `false`: sin consola web |
| `lidar` | `auto` | `auto`: el lidar real si está enchufado; `sim`: uno de mentira; `off` |
| `pico` | `true` | `false`: sin puente con la Pico de los sensores de distancia |
| `sim` | `false` | `true`: todo el droide simulado (`r2_sim`): una habitación, sensores de mentira y un Mega falso con el puente de verdad, para probar los modos sin riesgo |

En la Pi los argumentos van en `R2D2_ARGS` (`/etc/default/r2d2`), por ejemplo `R2D2_ARGS="sim:=true"`,
y luego `sudo systemctl restart r2d2`.

El nombre es histórico: el seguimiento del dome fue la primera demo y el launch creció a su alrededor.
