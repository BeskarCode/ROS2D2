# r2_shadow_bridge

El puente entre ROS 2 y el Arduino Mega de ShadowMD. **Es el único nodo que toca el
puerto serie**: los demás publican lo que quieren y el puente lo traduce a las órdenes
de texto que entiende el firmware (`ROS:FOOT:`, `ROS:DOME:`, `ROS:AUTO:`, `ROS:TRACK:`, `MD:`, `S1:`, `S3:`).
El protocolo completo está en `PCSerialProtocol.md` de ShadowMDLite.

## El modo autónomo y el seguimiento de caras

Son dos modos **independientes**, y los dos se encienden solo desde el mando:

- **Modo autónomo (foot): PS + L2 en el mando del foot.** Lo apagan la misma
  combinación, tocar el stick del foot, perder ese mando, o la Pi (servicio
  `/r2/auto_mode/disable`). Después el foot se queda quieto hasta que se vuelva a activar.
- **Seguimiento de caras (el dome): PS + L2 en el mando del dome.** Lo apagan la misma
  combinación, perder el mando del dome, o la Pi (servicio `/r2/track_mode/disable`). El
  stick del dome no lo apaga: manda él y el seguimiento vuelve a los 2 s. Hace falta mando
  de dome.

Así el dome puede mirar a la gente con el droide parado, o el foot moverse solo sin que
el dome se mueva. El puente publica cada estado en `/r2/auto_mode` y `/r2/track_mode`, y
mientras uno está apagado no manda nada a su parte (foot o dome) aunque alguien publique
velocidades.

## Topics, servicio y parámetros

| | Nombre | Tipo | Qué es |
|---|---|---|---|
| in | `/foot/cmd_vel` | `geometry_msgs/Twist` | Velocidad del foot: `linear.x` en m/s, `angular.z` en rad/s |
| in | `/dome/speed_cmd` | `std_msgs/Int16` | Velocidad del dome (unidades del SyRen) |
| in | `/mega/command` | `std_msgs/String` | Órdenes `MD:`, `S1:`, `S3:` (sonidos, paneles, luces) |
| out | `/r2/auto_mode` | `std_msgs/Bool` (latched) | Modo autónomo activo o no |
| out | `/r2/auto_mode/reason` | `std_msgs/String` (latched) | Por qué se apagó: `boot`, `button`, `stick`, `controller`, `pi`, `disconnected` |
| out | `/mega/connected` | `std_msgs/Bool` (latched) | Puerto serie abierto o no |
| out | `/mega/log` | `std_msgs/String` | Todo lo que dice el Mega |
| out | `/r2/track_mode` | `std_msgs/Bool` (latched) | Seguimiento de caras activo o no |
| out | `/r2/track_mode/reason` | `std_msgs/String` (latched) | Por qué se apagó: `boot`, `button`, `controller`, `pi`, `disconnected` |
| srv | `/r2/auto_mode/disable` | `std_srvs/Trigger` | Apaga el modo autónomo |
| srv | `/r2/track_mode/disable` | `std_srvs/Trigger` | Apaga el seguimiento de caras |

| Parámetro | Por defecto | Qué es |
|---|---|---|
| `port` | `/dev/r2-mega` | Puerto del Mega |
| `rate_hz` | 15 | Órdenes por segundo mientras hay movimiento |
| `drive_units_per_mps` | 50 | Calibración del avance (ver abajo) |
| `turn_units_per_radps` | 30 | Calibración del giro |
| `max_linear` | 0,4 m/s | Tope de avance en la Pi (el Mega tiene el suyo, más duro) |
| `max_angular` | 0,6 rad/s | Tope de giro |

Igual que con el dome, mientras haya movimiento manda la orden 15 veces por segundo; con
velocidad 0, o si las órdenes dejan de llegar, manda **una** parada y se calla.

## Calibrar el foot

El foot no tiene encoders, así que hay que medir una vez cuánto anda el R2 con cada
número de unidades. En el suelo, con sitio alrededor y el puente en marcha:

```
ros2 run r2_shadow_bridge foot_calibrate --drive 20 --seconds 3    # luego mide los metros
ros2 run r2_shadow_bridge foot_calibrate --turn 15 --seconds 4     # luego cuenta las vueltas
```

El script espera a que actives el modo con PS + L2, mueve el foot esos segundos, te pide
la medida y te da el valor de `drive_units_per_mps` o `turn_units_per_radps`. El stick
lo para en cualquier momento, como siempre.

## Probarlo sin el R2

`docker/auto_bench.sh` arranca el puente contra un Mega simulado (`docker/fake_mega.py`)
y comprueba los dos modos paso a paso; con `VIDEO=<vídeo>` también el dome tracker.
