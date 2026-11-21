# ROS 2 packages

*En castellano: [README_es.md](README_es.md)*

Everything that runs on the Raspberry Pi inside R2. Each folder is a ROS 2 package; the service
`r2d2` starts them all with one launch file (`r2_bringup`).

| Package | What it does |
|---|---|
| [`r2_bringup`](r2_bringup) | The launch file that starts everything, with switches for what is plugged in |
| [`r2_camera`](r2_camera) | The cameras: USB or network (the ESP32-P4 dome camera), one node each |
| [`r2_vision`](r2_vision) | Finds faces (YuNet on the Pi, or read from a camera that finds them itself) and the colour to follow |
| [`r2_dome_tracker`](r2_dome_tracker) | Turns the dome towards the biggest face any camera sees |
| [`r2_shadow_bridge`](r2_shadow_bridge) | The only node that talks to the Mega (ShadowMD) over USB |
| [`r2_imu`](r2_imu) | The MPU6050 gyroscope and accelerometer (not in the main launch yet) |
| [`r2_sensors`](r2_sensors) | Where each sensor sits (`sensors.yaml`), the lidar's scan cut to what R2 does not hide, its motor |
| [`r2_pico_bridge`](r2_pico_bridge) | Talks to the Pico that reads the distance sensors (VL53L0X, HC-SR04) |
| [`r2_nav`](r2_nav) | The automatic modes: go to a point, go forward, patrol, follow a colour; and the odometry |
| [`r2_sim`](r2_sim) | A simulated room, R2 and Mega, to try everything without the droid |
| [`r2_web`](r2_web) | The web console on port 8080 |

## How they fit together

```
cameras ─► r2_camera ─► r2_vision (faces) ─► r2_dome_tracker ─┐
                         └► r2_vision (colour) ─► r2_nav follow ─┤
lidar ─► sllidar_ros2 ─► r2_sensors (scan_crop) ─► r2_nav ───────┤─► r2_shadow_bridge ─► Mega
Pico ─► r2_pico_bridge (/range/<name>) ─────────► r2_nav ────────┘        (USB serial)
                        r2_web (console) ◄──► rosbridge ◄──► every topic
```

The Mega stays in charge of the hardware: the controller always wins, the feet move only with an
automatic mode on and the dome only with face tracking or a mode on; if the Pi goes quiet for
300 ms the Mega stops them.

## Build and run

On the Pi, `setup/setup_r2_brain.sh` installs ROS 2 and builds this workspace in `~/r2_ws`; from a
computer, `setup/deploy.sh` copies and rebuilds what changed (see [`setup`](../../setup)). By hand:

```
cd ~/r2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch r2_bringup dome_tracker.launch.py            # or sim:=true, lidar:=sim, mega:=false...
```

The settings people edit (cameras, sensors, modes, navigation, the Pico board) live in
`~/.config/ros2d2/` once saved from the console, and win over each package's `config/`.
