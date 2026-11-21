# r2_bringup

*En castellano: [README_es.md](README_es.md)*

The launch file that starts ROS2D2: the one the `r2d2` service runs at boot.

```
ros2 launch r2_bringup dome_tracker.launch.py
```

It starts the cameras (`r2_camera`), their face finders (`r2_vision`), the colour marker, the dome
tracker, the Mega bridge, the sensors and the lidar's cut (`r2_sensors`), the Pico bridge, the
automatic modes (`r2_nav`) and the web console (`r2_web`). The lidar driver itself runs in its own
service, `r2d2-lidar`, started when the lidar is plugged in.

| Argument | Default | What it does |
|---|---|---|
| `port` | `/dev/r2-mega` | The Mega's serial port |
| `mega` | `true` | `false`: no Mega bridge (no Mega plugged in); the dome tracker then simulates the dome's turn |
| `web` | `true` | `false`: no web console |
| `lidar` | `auto` | `auto`: the real lidar if plugged in; `sim`: a pretend one; `off` |
| `pico` | `true` | `false`: no bridge to the Pico of the distance sensors |
| `sim` | `false` | `true`: the whole droid simulated (`r2_sim`): a room, pretend sensors and a fake Mega with the real bridge, to try the modes safely |

On the Pi the arguments go in `R2D2_ARGS` (`/etc/default/r2d2`), for example `R2D2_ARGS="sim:=true"`,
and `sudo systemctl restart r2d2`.

The name is historical: the dome tracker was the first demo, and the launch grew round it.
