# r2_sensors

*En castellano: [README_es.md](README_es.md)*

The droid's sensors as ROS sees them: where each one sits, the lidar's scan and its motor.
Everything comes from `sensors.yaml` (`config/`, or `~/.config/ros2d2/` once saved from Setup →
Sensors): each sensor's type, position, where it points, field of view, range, whether it is in use.

| Node | What it does |
|---|---|
| `sensor_tf` | Each sensor's pose on `/tf_static` (`base_link` → `<name>_link`); saving the file moves them within a second |
| `scan_crop` | `/scan_raw` → `/scan` without the rays R2's own body hides (the lidar sits on the front foot and only sees ahead). The blind sectors set in the console are applied by the lidar driver |
| `lidar_motor` | Spins the lidar's motor as `sensors.yaml` says: `always`, `with_modes` (only while a mode is on) or `off` |
| `fake_lidar` | A pretend lidar (`lidar:=sim`): a small room with a chair leg, seen from where the lidar is |

```
ros2 launch r2_sensors sensors.launch.py
ros2 launch r2_sensors lidar_driver.launch.py     # the RPLIDAR C1 (sllidar_ros2); the r2d2-lidar service runs it
```

The lidar's driver is a fork of `sllidar_ros2` that also publishes the lidar's info (`/lidar/info`)
and takes the motor and scan mode from the console. `config.py` reads and checks `sensors.yaml`
(tested with pytest); the console uses the same rules.
