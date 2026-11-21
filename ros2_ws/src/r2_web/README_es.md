# r2_web

*In English: [README.md](README.md)*

La consola web de ROS2D2, en `http://<pi>:8080`. Cómo se usa está en el
[manual](../../../MANUAL_es.md) ([English](../../../MANUAL.md)); aquí, cómo está hecha.

- **`www/`**: las páginas (Console, Navigation, Setup) y sus scripts, módulos ES sin paso de
  compilación. Hablan con ROS por **rosbridge** (`ws://<pi>:9090`): topics y servicios directamente
  desde el navegador. `console.css` tiene los colores y tamaños comunes; la lógica sin página
  (formatos, el mando del Remote, los atajos, las cuentas de los sensores...) va en sus propios
  módulos, probados con `node --test test/*.mjs`.
- **`r2_web/web_server_node.py`** (`web_console`): sirve las páginas y una pequeña API HTTP para lo
  que no se puede hacer con topics: leer y guardar los ajustes YAML (cámaras, sensores, modos,
  navegación, la placa de la Pico) en `~/.config/ros2d2/`, las cámaras USB enchufadas, la telemetría y
  los datos de la Pi (`/api/system`), el estado de las cámaras del dome, el canal WiFi de R2, el USB y
  los ajustes del lidar, y la actualización del firmware de la Pico desde GitHub. Cada parte es su
  propio módulo (`*_api.py`), probado con pytest. También vigila rosbridge y lo reinicia si deja de
  pasar mensajes.

```
ros2 launch r2_web web.launch.py
```

La ventana **Remote** (`www/remote.js`, `padlogic.js`, `shortcuts.js`) maneja dos PS3 Nav virtuales
por `/pad/foot` y `/pad/dome`; el puente del Mega se los manda al Mega como `ROS:PAD`. Sus atajos siguen
el mapa de botones de ShadowMD Lite ([CheatSheet](https://github.com/BeskarCode/ShadowMDLite/blob/main/CheatSheet.md)).

El código de terceros de `www/vendor` (three.js y sus complementos, Font Awesome) mantiene su propia licencia.
