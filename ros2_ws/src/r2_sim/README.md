# r2_sim

*En castellano: [README_es.md](README_es.md)*

A simulator to try the modes and the console without the droid, and without risk: a room with
obstacles, a pretend R2 and a pretend Mega.

```
ros2 launch r2_bringup dome_tracker.launch.py sim:=true
```

| Node | What it does |
|---|---|
| `sim_world` | The room. R2 moves with what the **real** Mega bridge sends to the fake Mega (`ROS:FOOT:`, each lasting 0.3 s as on the Mega), and its pretend lidar and distance sensors (with noise) publish on the same topics as the real ones: `/scan_raw`, `/range/<name>`, `/odom`. Rooms, obstacles and a person wearing the colour to follow are edited from the console's Navigation page |
| `fake_mega` | A pretend ShadowMD Mega on a pty: it answers the ROS2D2 protocol like the firmware (`ROS:AUTO`, `ROS:TRACK`, `ROS:BIND`...) and its controllers are pretend too (the console's mode buttons) |

The navigation runs exactly as on the droid: only the world around it is pretend.
