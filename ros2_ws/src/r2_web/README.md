# r2_web

*En castellano: [README_es.md](README_es.md)*

The ROS2D2 web console, on `http://<pi>:8080`. How to use it is in the
[user manual](../../../MANUAL.md) ([castellano](../../../MANUAL_es.md)); this is how it is made.

- **`www/`**: the pages (Console, Navigation, Setup) and their scripts, plain ES modules with no
  build step. They talk to ROS through **rosbridge** (`ws://<pi>:9090`): topics and services straight
  from the browser. `console.css` holds the shared colours and sizes; the logic with no page in it
  (formatting, the remote's pad, the shortcuts, the sensor maths...) is in its own modules, tested
  with `node --test test/*.mjs`.
- **`r2_web/web_server_node.py`** (`web_console`): serves the pages and a small HTTP API for what
  topics cannot do: read and save the YAML settings (cameras, sensors, modes, navigation, the Pico
  board) in `~/.config/ros2d2/`, the USB cameras plugged in, the Pi's telemetry and info
  (`/api/system`), the dome cameras' status, R2's WiFi channel, the lidar's USB and settings, and
  the Pico firmware update from GitHub. Each part is its own module (`*_api.py`), tested with pytest.
  It also watches rosbridge and restarts it if it stops passing messages.

```
ros2 launch r2_web web.launch.py
```

The **phone view** (`www/phone.html`, `phone.js`, `phonelogic.js`) drives R2 from a phone: two
sticks, the actions with favourites, the modes and STOP; `remote_api.py` keeps its settings
(`remote.yaml`: the sticks' limit, guest mode, favourites). It and the Remote window send through
`padlink.js`.

The **Remote** window (`www/remote.js`, `padlogic.js`, `shortcuts.js`) drives two virtual PS3 Navs
through `/pad/foot` and `/pad/dome`; the Mega bridge sends them to the Mega as `ROS:PAD`. Its
shortcuts follow ShadowMD Lite's button map ([CheatSheet](https://github.com/BeskarCode/ShadowMDLite/blob/main/CheatSheet.md)).

Third-party code in `www/vendor` (three.js and its add-ons, Font Awesome) keeps its own licence.
