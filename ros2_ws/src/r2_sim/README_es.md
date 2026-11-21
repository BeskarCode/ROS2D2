# r2_sim

*In English: [README.md](README.md)*

Un simulador para probar los modos y la consola sin el droide, y sin riesgo: una habitación con
obstáculos, un R2 de mentira y un Mega de mentira.

```
ros2 launch r2_bringup dome_tracker.launch.py sim:=true
```

| Nodo | Qué hace |
|---|---|
| `sim_world` | La habitación. R2 se mueve con lo que el puente del Mega **de verdad** le manda al Mega falso (`ROS:FOOT:`, cada uno dura 0,3 s como en el Mega), y su lidar y sus sensores de distancia de mentira (con ruido) publican en los mismos topics que los reales: `/scan_raw`, `/range/<nombre>`, `/odom`. Las habitaciones, los obstáculos y una persona con el color a seguir se editan desde la página Navigation de la consola |
| `fake_mega` | Un Mega ShadowMD de mentira en un pty: contesta al protocolo de ROS2D2 como el firmware (`ROS:AUTO`, `ROS:TRACK`, `ROS:BIND`...) y sus mandos también son de mentira (los botones de modo de la consola) |

La navegación corre exactamente igual que en el droide: solo el mundo de alrededor es de mentira.
