# r2_dome_tracker

*In English: [README.md](README.md)*

Gira el dome para mirar a la cara más cercana. Cada cámara de `cameras.yaml` tiene una dirección en el
dome (`yaw_deg`, + = derecha) y un campo de visión (`hfov_deg`), así que una cara en cualquier sitio
de cualquier imagen se convierte en un ángulo desde el frente del dome; el dome gira hacia la cara más
grande que vea cualquier cámara. La ley de control viene de la prueba de concepto DomeTracker y se
ajustó en el droide.

Solo mueve el dome mientras el **seguimiento de caras** está encendido (PS + L2 en el Nav del dome; el
Mega lo dice en `/r2/track_mode`), y se calla mientras hay un modo automático encendido (el modo mueve
el dome).

| Topic | Tipo | |
|---|---|---|
| `/cameras/<cámara>/faces` | `vision_msgs/Detection2DArray` | entra: las caras, la más grande primero |
| `/cameras/<cámara>/camera_info` | `sensor_msgs/CameraInfo` | entra: el ancho de la imagen |
| `/r2/track_mode` | `std_msgs/Bool` | entra: seguimiento de caras encendido o no |
| `/r2/mode` | `std_msgs/String` | entra: qué modo automático está encendido |
| `/dome/angle_reset` | `std_msgs/Empty` | entra: el dome vuelve a mirar al frente (la estimación de la consola) |
| `/dome/speed_cmd` | `std_msgs/Int16` | sale: velocidad del dome en unidades `DM:` de ShadowMD, ~15 por segundo; la manda el puente del Mega |
| `~/status` | `std_msgs/String` | sale: `tracking`, `no face`, `track off`, `mode` o `disabled` |

Ajustes en `config/dome_tracker.yaml`: velocidades (`min_speed`, `max_speed`), la zona muerta, la amortiguación (`kd`), `invert` y `deg_per_s_at_80` (lo rápido que gira el dome: mide una vuelta completa a velocidad 80). `control.py` tiene la
ley de control sin ROS, probada con pytest.
