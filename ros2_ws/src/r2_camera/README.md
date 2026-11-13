# r2_camera

*En castellano: [README_es.md](README_es.md)*

ROS2D2's camera node. There is one instance per camera, and it works both for USB webcams and for
network cameras (an ESP32-CAM, for example).

## Start

```
ros2 launch r2_camera cameras.launch.py
```

It starts one camera for each block of `config/cameras.yaml`. Each one publishes on:

| Topic | Type | What for |
|---|---|---|
| `/cameras/<name>/image_raw` | `sensor_msgs/Image` (bgr8) | Detection (dome tracker...) |
| `/cameras/<name>/image_raw/compressed` | `sensor_msgs/CompressedImage` (JPEG) | The web console, watching it from another computer |

It only publishes (and compresses) while someone is listening to that topic. Each picture carries
**the time it was taken**, so the dome control can make up for the camera's delay.

## Parameters

| Parameter | Default | |
|---|---|---|
| `source` | `0` | `/dev/video0`, `/dev/v4l/by-id/...` or a `http://.../stream` URL |
| `width`, `height`, `fps` | 640, 480, 30 | USB only; a network camera picks its own format |
| `fourcc` | `MJPG` | USB format; with MJPG most webcams give their 30 fps |
| `frame_id` | `camera` | The camera's name in the robot model |
| `rotate` | 0 | 0, 90, 180 or 270 (clockwise) |
| `flip` | `none` | `none`, `h`, `v` or `both` |
| `publish_raw`, `publish_compressed` | true, true | |
| `jpeg_quality` | 70 | 1–100 |
| `reconnect_sec` | 2.0 | Wait before trying again if the camera drops |

All of them can be changed while it runs. If you change the source or the format, the camera is
opened again:

```
ros2 param set /cameras/front/camera rotate 180
ros2 param set /cameras/front/camera source http://192.168.68.150:81/stream
```

If the camera is unplugged or stops answering, the node keeps trying on its own.
