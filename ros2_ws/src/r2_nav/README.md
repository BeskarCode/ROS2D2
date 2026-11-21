# r2_nav

*En castellano: [README_es.md](README_es.md)*

The automatic modes and the odometry. Nothing here moves R2 on its own: a mode is switched on only
from the controller (the combination given to it in Setup → Modes), and the Mega stops the feet if
the Pi goes quiet or the stick is touched.

| Node | What it does |
|---|---|
| `navigator` | **Go to a point** (towards `/nav/goal`), **go forward** (straight on, looking for a way out when boxed in) and **patrol** (round the route on `/nav/patrol`). It steers round what the lidar and the distance sensors see, stops at a safety circle, backs up, turns or waits when blocked, gives up after a few tries, and plays a sound on each event |
| `follow` | **Follow a colour**: drives the feet and the dome after the colour marker (`/marker`, from `r2_vision`), keeping its distance; stops when it loses it |
| `dead_reckoning` | Odometry without wheel encoders: what really went to the Mega, plus the IMU's heading and the lidar's odometry (`rf2o_laser_odometry`) when they are there. Not used in the simulator, which has its own |

The modes only drive where a sensor looks, and a sensor that stops answering counts as "something
there", never as "the way is clear".

| Topic | |
|---|---|
| `/foot/cmd_vel` (out) | the feet, 10 Hz with acceleration ramps; the Mega bridge sends it as `ROS:FOOT:` |
| `/dome/speed_cmd` (out) | the dome, while following a colour |
| `/mega/command` (out) | the sounds of the events (`S1:$..`) |
| `/nav/state`, `/follow/state` (out) | JSON for the console's Navigation page |
| `/scan`, `/range/<name>`, `/odom` (in) | what it sees and where it is |
| `/r2/auto_mode`, `/r2/mode` (in) | from the Mega bridge: whether a mode is on, and which |

```
ros2 launch r2_nav nav.launch.py
```

Settings: `config/nav.yaml` (speeds, safety circle, tries, sounds; edited in Navigation → Settings)
and `config/modes.yaml` (each mode's combination and the colour to follow; Setup → Modes). The logic
of each mode is in plain Python (`nav_core.py`, `patrol.py`, `follow_core.py`, `odometry.py`),
tested with pytest and in the simulator (`r2_sim`).
