# r2_camera

Nodo de cámara del ROS2D2. Hay una instancia por cámara y sirve tanto para
webcams USB como para cámaras por red (por ejemplo, una ESP32-CAM).

## Arrancar

```
ros2 launch r2_camera cameras.launch.py
```

Arranca una cámara por cada bloque de `config/cameras.yaml`. Cada una publica en:

| Topic | Tipo | Para qué |
|---|---|---|
| `/cameras/<nombre>/image_raw` | `sensor_msgs/Image` (bgr8) | Detección (dome tracker...) |
| `/cameras/<nombre>/image_raw/compressed` | `sensor_msgs/CompressedImage` (JPEG) | Consola web, verlo desde otro equipo |

Solo se publica (y se comprime) cuando alguien está escuchando ese topic.
Cada imagen lleva la **hora en que se capturó**, para que el control del dome
pueda compensar el retraso de la cámara.

## Parámetros

| Parámetro | Por defecto | |
|---|---|---|
| `source` | `0` | `/dev/video0`, `/dev/v4l/by-id/...` o una URL `http://.../stream` |
| `width`, `height`, `fps` | 640, 480, 30 | Solo para USB; la cámara de red decide su formato |
| `fourcc` | `MJPG` | Formato USB; con MJPG la mayoría de webcams dan los 30 fps |
| `frame_id` | `camera` | Nombre de la cámara en el modelo del robot |
| `rotate` | 0 | 0, 90, 180 o 270 (sentido horario) |
| `flip` | `none` | `none`, `h`, `v` o `both` |
| `publish_raw`, `publish_compressed` | true, true | |
| `jpeg_quality` | 70 | 1–100 |
| `reconnect_sec` | 2.0 | Espera antes de reintentar si la cámara se cae |

Todos se pueden cambiar en marcha. Si cambias la fuente o el formato, la cámara se reabre:

```
ros2 param set /cameras/front/camera rotate 180
ros2 param set /cameras/front/camera source http://192.168.68.150:81/stream
```

Si la cámara se desconecta o no responde, el nodo lo reintenta solo.
