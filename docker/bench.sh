#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# ROS2D2 test bench, run inside the ros2d2-dev container:
#
#   docker run --rm -v <ROS2D2>:/r2 -v <video folder>:/media ros2d2-dev \
#       bash /r2/docker/bench.sh /media/dome-tracker-follows-me.mp4 [seconds]
#
# Builds the workspace, fakes the Mega with a socat pty pair, starts the whole
# dome tracker demo with the video as the camera, and records what the Mega
# would have received. Results end up in /r2/docker/bench-out/.
#
# With the webcam (see webcam_mjpeg.py), set FEEDBACK to its state URL: the test
# page at http://localhost:8081/ then shows each phase, and the recording only
# starts when you press Start there and lasts [seconds] or until you press Stop.
#
#   docker run --rm -v <ROS2D2>:/r2 -e FEEDBACK=http://host.docker.internal:8081/state #       ros2d2-dev bash /r2/docker/bench.sh http://host.docker.internal:8081/stream 40
set -eo pipefail

VIDEO=${1:?usage: bench.sh <video> [seconds]}
SECS=${2:-20}
OUT=/r2/docker/bench-out
mkdir -p "$OUT"
rm -f "$OUT"/*

# Tell the test page (if any) what is going on: state '{"phase": "build"}'
state() {
    [ -n "$FEEDBACK" ] || return 0
    python3 -c 'import sys, urllib.request as u
u.urlopen(u.Request(sys.argv[1], sys.argv[2].encode()), timeout=1)' "$FEEDBACK" "$1" || true
}
started() {
    python3 -c 'import json, sys, urllib.request as u
sys.exit(0 if json.load(u.urlopen(sys.argv[1], timeout=1)).get("start") else 1)' "$FEEDBACK" 2>/dev/null
}

state '{"reset": true, "phase": "build"}'
source /opt/ros/jazzy/setup.bash

echo "== build"
rm -rf /ws/src && mkdir -p /ws && cp -r /r2/ros2_ws/src /ws/src
cd /ws
colcon build --symlink-install 2>&1 | tail -5
source install/setup.bash

echo "== unit tests"
colcon test --event-handlers console_direct- >/dev/null 2>&1 || true
colcon test-result --verbose | tail -3

echo "== fake Mega"
socat -d pty,raw,echo=0,link=/tmp/mega pty,raw,echo=0,link=/tmp/mega-side &
SOCAT=$!
sleep 1
# A pretend Mega that logs what it receives (with a timestamp per line) and speaks the
# autonomous-mode protocol: the dome only follows faces once PS + L2 is "pressed"
python3 /r2/docker/fake_mega.py /tmp/mega-side "$OUT/mega_rx.log" /tmp/mega-ctl &
READER=$!

cat > /tmp/cameras.yaml <<EOF
front:
  source: $VIDEO
  width: 640
  height: 480
  fps: 30
  fourcc: ""
  frame_id: dome_camera_front
EOF

echo "== launch"
state '{"phase": "starting"}'
ros2 launch r2_bringup dome_tracker.launch.py port:=/tmp/mega config:=/tmp/cameras.yaml \
    > "$OUT/launch.log" 2>&1 &
LAUNCH=$!
sleep 6
timeout 8 ros2 topic hz /cameras/front/image_raw > "$OUT/camera_hz.txt" 2>&1 || true
ros2 node list --no-daemon --spin-time 3 > "$OUT/nodes.txt" 2>&1

if [ -n "$FEEDBACK" ]; then
    echo "== waiting for Start on the test page (5 min max)"
    state '{"phase": "ready"}'
    for _ in $(seq 600); do started && break; sleep 0.5; done
fi

echo "== autonomous mode on (pretend PS + L2)"
echo button > /tmp/mega-ctl
sleep 1

echo "== recording ($SECS s)"
ros2 topic echo --csv /dome/speed_cmd > "$OUT/speed_cmd.csv" 2>/dev/null &
SPEED=$!
if [ -n "$FEEDBACK" ]; then
    python3 /r2/docker/bench_feedback.py "$FEEDBACK" "$SECS"
else
    sleep "$SECS"
fi
# SIGTERM, not SIGINT: background jobs of a script ignore SIGINT
kill $SPEED; wait $SPEED 2>/dev/null || true

# Stop ROS first and let the bridge close the port, then the fake Mega
kill $LAUNCH; wait $LAUNCH 2>/dev/null || true
kill $READER $SOCAT 2>/dev/null || true

echo "== results"
echo "nodes:";            cat "$OUT/nodes.txt"
echo "camera rate:";      grep "average rate" "$OUT/camera_hz.txt" | tail -1
echo "speed_cmd msgs:";   wc -l < "$OUT/speed_cmd.csv"
echo "  nonzero:";        grep -cv '^0$' "$OUT/speed_cmd.csv" || true
echo "  min/max:";        sort -n "$OUT/speed_cmd.csv" | sed -n '1p;$p' | tr '\n' ' '; echo
NEG=$(grep -c '^-' "$OUT/speed_cmd.csv" || true)
POS=$(grep -cE '^[1-9]' "$OUT/speed_cmd.csv" || true)
echo "  negative/positive: $NEG / $POS"
echo "Mega received:";    grep -c "ROS:DOME:" "$OUT/mega_rx.log"
echo "  first lines:";    grep "ROS:DOME:" "$OUT/mega_rx.log" | head -5 || true
echo "errors in launch:"; grep -iE "error|traceback|exception" "$OUT/launch.log" | head -10 || echo "  none"

state "{\"phase\": \"done\", \"summary\": \"$(wc -l < "$OUT/speed_cmd.csv") ordenes al dome: $NEG negativas, $POS positivas. El Mega recibio $(grep -c ROS:DOME: "$OUT/mega_rx.log") lineas ROS:DOME:\"}"
