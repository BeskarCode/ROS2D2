# r2_vision

*En castellano: [README_es.md](README_es.md)*

What the cameras see: faces for the dome, and the colour for the follow-a-colour mode.

| Node | What it does |
|---|---|
| `face_detector` | Finds faces in a camera's picture with OpenCV's YuNet (`models/`), one node per camera. Publishes them as standard detections, biggest first, and a picture with the boxes drawn only while someone watches it |
| `remote_faces` | For a camera that finds faces itself (the ESP32-P4 dome camera): reads them from it (`:82/faces`, a few numbers per picture) and publishes them exactly as `face_detector` does, so no video has to travel for the dome to follow faces |
| `color_marker` | The colour to follow: where it is in the picture (`/marker`), from the camera picture, or from the dome camera when it finds the colour itself. Also the console's colour picking and preview (Setup → Modes) |

| Topic | |
|---|---|
| `/cameras/<camera>/faces` | `vision_msgs/Detection2DArray`, pixels of the picture |
| `/cameras/<camera>/faces/image/compressed` | the picture with the boxes, only when watched |
| `/marker` | JSON `{seen, bearing, area, cx, cy, t}` for `r2_nav follow` |
| `/marker/pick`, `/marker/pick_result`, `/marker/mask/compressed` | the console's colour picker |

```
ros2 launch r2_vision face_detectors.launch.py
```

`face_detectors.launch.py` starts one `face_detector` or `remote_faces` per camera in `cameras.yaml`,
depending on whether the camera finds the faces itself (`detect: camera`). Needs OpenCV 4.8 or newer.
