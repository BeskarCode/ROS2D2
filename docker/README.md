# docker

*En castellano: [README_es.md](README_es.md)*

A test bench on a PC: the same ROS 2 in a container, with a video file or a webcam instead of the dome
camera and a fake Mega (a socat pty pair) instead of the real one. Nothing here runs on the droid.

```
docker build -t ros2d2-dev docker
docker run --rm -v <ROS2D2 folder>:/r2 -v <video folder>:/media ros2d2-dev bash /r2/docker/bench.sh /media/video.mp4 25
```

| File | What it does |
|---|---|
| `Dockerfile` | The `ros2d2-dev` image: ROS 2, OpenCV, socat and the Python tools the nodes need |
| `bench.sh` | The dome tracker demo with a video (or a webcam) as the camera: builds the workspace, fakes the Mega and records what it would have received. Results in `bench-out/` (not in git) |
| `webcam_mjpeg.py` | **On Windows**: serves a PC webcam as an MJPEG stream, like the dome camera, with a test page at `http://localhost:8081/` (Start, Stop) |
| `bench_feedback.py` | Tells that test page what the bench sees while you move (a face or not, the dome speed) |
| `auto_bench.sh` | The Mega bridge's autonomous mode and face tracking, against the fake Mega |
| `nav_bench.sh` + `nav_e2e.py` | The navigation simulator end to end: switch a mode on, reach a goal, give up on an unreachable one |
| `odom_bench.sh` + `odom_check.py` | The dead reckoning and the lidar's odometry against the simulator's true pose |
| `imu_bench.sh` | The IMU node with a fake MPU6050 (`fakes/smbus2.py`) turning at 10 °/s |
| `fake_mega.py` | Kept for the benches; the fake Mega now lives in `r2_sim` |

The top of each script says how to run it.
