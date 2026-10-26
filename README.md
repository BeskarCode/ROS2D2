# ROS2D2

A ROS 2 brain for an R2-D2 that runs ShadowMD. A Raspberry Pi 4 sits on top of the
droid's Arduino Mega: the Pi handles the senses (cameras, voice, later a lidar) and
decides what to do, and the Mega keeps driving the motors, sounds and lights.

The controller always wins: touch the stick and control is back with you at once.
The Mega also stops the dome if the Pi goes quiet for 300 ms.

First demo: the dome turns to look at you. It is the [DomeTracker](https://github.com/BeskarCode/DomeTracker)
proof of concept, split into ROS 2 nodes.

```
 camera ──image_raw──> face detector ──faces──> dome tracker ──/dome/speed_cmd──> Mega bridge ──DM:<speed>──> Mega
```

## Packages (`ros2_ws/src`)

| Package | Node | What it does |
|---|---|---|
| `r2_camera` | `camera_node` | USB or network (ESP32-CAM) camera, one instance per camera |
| `r2_vision` | `face_detector` | OpenCV YuNet face detector, closest face first |
| `r2_dome_tracker` | `dome_tracker` | Dome speed from the face position (control law tuned on the droid) |
| `r2_shadow_bridge` | `mega_bridge`, `foot_calibrate` | The only node that talks to the Mega over USB serial; the feet move only in autonomous mode (PS + L2 on the foot controller), the dome only with face tracking on (PS + L2 on the dome controller); the two are independent |
| `r2_imu` | `imu_node` | MPU6050 gyro and accelerometer over I2C, plus a Madgwick filter |
| `r2_sensors` | `sensor_tf`, `fake_lidar`, `scan_crop` | Where the lidar and the distance sensors (VL53L0X, HC-SR04 on a Pico) sit, from `sensors.yaml` (edited in the web console: Setup → Sensors), on `/tf_static`; the lidar's `/scan` cut to what the droid does not hide; a pretend lidar with `lidar:=sim` |
| `r2_web` | `web_console` | Web console on port 8080: cameras, faces, 3D dome, camera and sensor setup |
| `r2_bringup` | | Launch files: `ros2 launch r2_bringup dome_tracker.launch.py` |

## Raspberry Pi setup

Ubuntu Server 24.04 (64-bit) on a Pi 4, then:

```
sudo bash setup/setup_r2_brain.sh
```

It installs ROS 2 Jazzy, the camera and web tools, and the serial port permissions.
Takes 1.5 to 2.5 hours, mostly waiting on the microSD: use a fast A2 card.

## Test bench on a PC (Docker)

The same ROS 2 Jazzy in a container, with a video file or a webcam instead of the
dome camera and a fake Mega (a socat pty pair) instead of the real one:

```
docker build -t ros2d2-dev docker
docker run --rm -v <this folder>:/r2 -v <video folder>:/media ros2d2-dev \
    bash /r2/docker/bench.sh /media/video.mp4 25
```

With a webcam on Windows, `python docker/webcam_mjpeg.py 1` serves it as an MJPEG
stream (the same format as an ESP32-CAM) and opens a test page at
<http://localhost:8081/> with Start and Stop buttons. See the top of `docker/bench.sh`.
