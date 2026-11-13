# r2_shadow_bridge

*En castellano: [README_es.md](README_es.md)*

The bridge between ROS 2 and ShadowMD's Arduino Mega. **It is the only node that touches the serial
port**: the others publish what they want and the bridge turns it into the text commands the
firmware understands (`ROS:FOOT:`, `ROS:DOME:`, `ROS:AUTO:`, `ROS:TRACK:`, `MD:`, `S1:`, `S3:`). The
whole protocol is in ShadowMDLite's `PCSerialProtocol.md`.

## The autonomous mode and face tracking

They are two **independent** modes, and both are switched on only from the controller:

- **Autonomous mode (foot): PS + L2 on the foot controller.** It is switched off by the same
  combination, by touching the foot stick, by losing that controller, or by the Pi (service
  `/r2/auto_mode/disable`). Afterwards the foot stays still until it is switched on again.
- **Face tracking (the dome): PS + L2 on the dome controller.** It is switched off by the same
  combination, by losing the dome controller, or by the Pi (service `/r2/track_mode/disable`). The
  dome stick does not switch it off: the stick takes over and tracking comes back after 2 s. It
  needs a dome controller.

So the dome can look at people with the droid standing still, or the foot can move on its own
without the dome moving. The bridge publishes each state on `/r2/auto_mode` and `/r2/track_mode`,
and while one is off it sends nothing to its part (foot or dome), even if someone publishes speeds.

## Topics, services and parameters

| | Name | Type | What it is |
|---|---|---|---|
| in | `/foot/cmd_vel` | `geometry_msgs/Twist` | Foot speed: `linear.x` in m/s, `angular.z` in rad/s |
| in | `/dome/speed_cmd` | `std_msgs/Int16` | Dome speed (SyRen units) |
| in | `/mega/command` | `std_msgs/String` | `MD:`, `S1:`, `S3:` commands (sounds, panels, lights) |
| out | `/r2/auto_mode` | `std_msgs/Bool` (latched) | Autonomous mode on or off |
| out | `/r2/auto_mode/reason` | `std_msgs/String` (latched) | Why it went off: `boot`, `button`, `stick`, `controller`, `pi`, `disconnected` |
| out | `/mega/connected` | `std_msgs/Bool` (latched) | Serial port open or not |
| out | `/mega/log` | `std_msgs/String` | Everything the Mega says |
| out | `/r2/track_mode` | `std_msgs/Bool` (latched) | Face tracking on or off |
| out | `/r2/track_mode/reason` | `std_msgs/String` (latched) | Why it went off: `boot`, `button`, `controller`, `pi`, `disconnected` |
| srv | `/r2/auto_mode/disable` | `std_srvs/Trigger` | Switches the autonomous mode off |
| srv | `/r2/track_mode/disable` | `std_srvs/Trigger` | Switches face tracking off |

| Parameter | Default | What it is |
|---|---|---|
| `port` | `/dev/r2-mega` | The Mega's port |
| `rate_hz` | 15 | Commands per second while moving |
| `drive_units_per_mps` | 50 | Calibration of driving (see below) |
| `turn_units_per_radps` | 30 | Calibration of turning |
| `max_linear` | 0.4 m/s | Speed limit on the Pi (the Mega has its own, harder one) |
| `max_angular` | 0.6 rad/s | Turn limit |

As with the dome, while there is movement it sends the command 15 times a second; at speed 0, or if
the commands stop coming, it sends **one** stop and nothing more.

## Calibrating the foot

The foot has no encoders, so you measure once how far R2 goes with each number of units. On the
floor, with room around it and the bridge running:

```
ros2 run r2_shadow_bridge foot_calibrate --drive 20 --seconds 3    # then measure the metres
ros2 run r2_shadow_bridge foot_calibrate --turn 15 --seconds 4     # then count the turns
```

The script waits for you to switch the mode on with PS + L2, moves the foot for those seconds, asks
you for the measurement and gives you the value of `drive_units_per_mps` or `turn_units_per_radps`.
The stick stops it at any moment, as always.

## Trying it without R2

`docker/auto_bench.sh` starts the bridge against a simulated Mega (`docker/fake_mega.py`) and checks
both modes step by step; with `VIDEO=<video>` the dome tracker too.
