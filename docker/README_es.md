# docker

*In English: [README.md](README.md)*

Un banco de pruebas en el PC: el mismo ROS 2 en un contenedor, con un vídeo o una webcam en lugar de la
cámara del dome y un Mega falso (un par de pty de socat) en lugar del de verdad. Nada de esto corre en
el droide.

```
docker build -t ros2d2-dev docker
docker run --rm -v <carpeta de ROS2D2>:/r2 -v <carpeta de vídeos>:/media ros2d2-dev bash /r2/docker/bench.sh /media/video.mp4 25
```

| Fichero | Qué hace |
|---|---|
| `Dockerfile` | La imagen `ros2d2-dev`: ROS 2, OpenCV, socat y las herramientas de Python que necesitan los nodos |
| `bench.sh` | La demo del seguimiento del dome con un vídeo (o una webcam) como cámara: compila el workspace, simula el Mega y apunta lo que le habría llegado. Resultados en `bench-out/` (fuera de git) |
| `webcam_mjpeg.py` | **En Windows**: sirve una webcam del PC como vídeo MJPEG, igual que la cámara del dome, con una página de prueba en `http://localhost:8081/` (Start, Stop) |
| `bench_feedback.py` | Le cuenta a esa página lo que ve el banco mientras te mueves (si hay cara, la velocidad del dome) |
| `auto_bench.sh` | El modo autónomo y el seguimiento de caras del puente del Mega, contra el Mega falso |
| `nav_bench.sh` + `nav_e2e.py` | El simulador de navegación de punta a punta: encender un modo, llegar a un objetivo, rendirse ante uno imposible |
| `odom_bench.sh` + `odom_check.py` | La odometría por estima y la del lidar contra la posición real del simulador |
| `imu_bench.sh` | El nodo de la IMU con un MPU6050 de mentira (`fakes/smbus2.py`) girando a 10 °/s |
| `fake_mega.py` | Se queda para los bancos; el Mega falso vive ahora en `r2_sim` |

Al principio de cada script pone cómo se ejecuta.
