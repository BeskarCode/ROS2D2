# r2_dome_tracker

*En castellano: [README_es.md](README_es.md)*

Turns the dome to look at the closest face. Each camera in `cameras.yaml` has a direction on the
dome (`yaw_deg`, + = right) and a field of view (`hfov_deg`), so a face anywhere in any picture
becomes an angle from the dome's front; the dome turns towards the biggest face seen by any camera.
The control law comes from the DomeTracker proof of concept and was tuned on the droid.

It only moves the dome while **face tracking** is on (PS + L2 on the dome Nav, the Mega says so on
`/r2/track_mode`), and stays quiet while an automatic mode is on (the mode moves the dome).

| Topic | Type | |
|---|---|---|
| `/cameras/<camera>/faces` | `vision_msgs/Detection2DArray` | in: the faces, biggest first |
| `/cameras/<camera>/camera_info` | `sensor_msgs/CameraInfo` | in: the picture's width |
| `/r2/track_mode` | `std_msgs/Bool` | in: face tracking on or off |
| `/r2/mode` | `std_msgs/String` | in: which automatic mode is on |
| `/dome/angle_reset` | `std_msgs/Empty` | in: the dome is facing front again (the console's estimate) |
| `/dome/speed_cmd` | `std_msgs/Int16` | out: dome speed in ShadowMD `DM:` units, ~15 a second; the Mega bridge sends it |
| `~/status` | `std_msgs/String` | out: `tracking`, `no face`, `track off`, `mode` or `disabled` |

Settings in `config/dome_tracker.yaml`: speeds (`min_speed`, `max_speed`), the dead zone, the damping (`kd`), `invert`, and `deg_per_s_at_80` (how fast the dome turns: measure a full turn at speed 80). `control.py` has the control
law without ROS, tested with pytest.
