# r2_vision

*In English: [README.md](README.md)*

Lo que ven las cámaras: caras para el dome, y el color para el modo seguir un color.

| Nodo | Qué hace |
|---|---|
| `face_detector` | Busca caras en la imagen de una cámara con YuNet de OpenCV (`models/`), un nodo por cámara. Las publica como detecciones estándar, la más grande primero, y una imagen con los recuadros dibujados solo mientras alguien la mira |
| `remote_faces` | Para una cámara que busca las caras ella sola (la cámara del dome ESP32-P4): se las lee (`:82/faces`, unos pocos números por imagen) y las publica igual que `face_detector`, así no hace falta que viaje vídeo para que el dome siga caras |
| `color_marker` | El color a seguir: dónde está en la imagen (`/marker`), desde la imagen de la cámara, o desde la cámara del dome cuando busca el color ella sola. También el elegir el color y la vista previa de la consola (Setup → Modes) |

| Topic | |
|---|---|
| `/cameras/<cámara>/faces` | `vision_msgs/Detection2DArray`, píxeles de la imagen |
| `/cameras/<cámara>/faces/image/compressed` | la imagen con los recuadros, solo si alguien la mira |
| `/marker` | JSON `{seen, bearing, area, cx, cy, t}` para `r2_nav follow` |
| `/marker/pick`, `/marker/pick_result`, `/marker/mask/compressed` | el selector de color de la consola |

```
ros2 launch r2_vision face_detectors.launch.py
```

`face_detectors.launch.py` arranca un `face_detector` o un `remote_faces` por cada cámara de
`cameras.yaml`, según si la cámara busca las caras ella sola (`detect: camera`). Necesita OpenCV 4.8 o
posterior.
