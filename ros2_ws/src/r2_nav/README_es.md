# r2_nav

*In English: [README.md](README.md)*

Los modos automáticos y la odometría. Aquí nada mueve a R2 por su cuenta: un modo solo se enciende
desde el mando (con la combinación que tenga en Setup → Modes), y el Mega para los pies si la Pi deja
de hablar o se toca el stick.

| Nodo | Qué hace |
|---|---|
| `navigator` | **Ir a un punto** (hacia `/nav/goal`), **avanzar** (recto, buscando salida cuando se ve encerrado) y **patrulla** (la ruta de `/nav/patrol`). Esquiva lo que ven el lidar y los sensores de distancia, se para en un círculo de seguridad, retrocede, gira o espera cuando se bloquea, se rinde tras unos intentos y suena en cada evento |
| `follow` | **Seguir un color**: mueve los pies y el dome detrás del marcador de color (`/marker`, de `r2_vision`), guardando la distancia; se para cuando lo pierde |
| `dead_reckoning` | Odometría sin encoders en las ruedas: lo que de verdad se mandó al Mega, más el rumbo de la IMU y la odometría del lidar (`rf2o_laser_odometry`) si están. No se usa en el simulador, que tiene la suya |

Los modos solo conducen hacia donde mira algún sensor, y un sensor que deja de contestar cuenta como
"hay algo", nunca como "el camino está libre".

| Topic | |
|---|---|
| `/foot/cmd_vel` (sale) | los pies, 10 Hz con rampas de aceleración; el puente del Mega lo manda como `ROS:FOOT:` |
| `/dome/speed_cmd` (sale) | el dome, mientras sigue un color |
| `/mega/command` (sale) | los sonidos de los eventos (`S1:$..`) |
| `/nav/state`, `/follow/state` (sale) | JSON para la página Navigation de la consola |
| `/scan`, `/range/<nombre>`, `/odom` (entra) | lo que ve y dónde está |
| `/r2/auto_mode`, `/r2/mode` (entra) | del puente del Mega: si hay un modo encendido, y cuál |

```
ros2 launch r2_nav nav.launch.py
```

Ajustes: `config/nav.yaml` (velocidades, círculo de seguridad, intentos, sonidos; se edita en
Navigation → Settings) y `config/modes.yaml` (la combinación de cada modo y el color a seguir; Setup →
Modes). La lógica de cada modo está en Python puro (`nav_core.py`, `patrol.py`, `follow_core.py`,
`odometry.py`), probada con pytest y en el simulador (`r2_sim`).
