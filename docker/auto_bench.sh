#!/bin/bash
# Autonomous mode check for the Mega bridge, inside the ros2d2-dev container:
#
#   docker run --rm -v <ROS2D2>:/r2 ros2d2-dev bash /r2/docker/auto_bench.sh
#
# A pretend Mega (docker/fake_mega.py) with a pretend controller: each step pokes it
# and checks what the bridge publishes and what reaches the Mega. Ends with ALL PASS,
# or FAIL <step> and exit 1.
set -o pipefail
source /opt/ros/jazzy/setup.bash

OUT=/r2/docker/bench-out
mkdir -p "$OUT"
LOG=$OUT/auto_mega_rx.log
: > "$LOG"

echo "== build"
rm -rf /ws/src && mkdir -p /ws && cp -r /r2/ros2_ws/src /ws/src
cd /ws
colcon build --symlink-install 2>&1 | tail -1
source install/setup.bash

echo "== pretend Mega"
socat pty,raw,echo=0,link=/tmp/mega pty,raw,echo=0,link=/tmp/mega-side &
SOCAT=$!
sleep 1
python3 /r2/docker/fake_mega.py /tmp/mega-side "$LOG" /tmp/mega-ctl &
MEGA=$!
sleep 1
ros2 run r2_shadow_bridge mega_bridge --ros-args -p port:=/tmp/mega -p open_wait:=0.5 \
    > "$OUT/auto_bridge.log" 2>&1 &
BRIDGE=$!

cleanup() { kill $BRIDGE $MEGA $SOCAT 2>/dev/null; wait 2>/dev/null; }
trap cleanup EXIT

fail() { echo "FAIL $1"; tail -5 "$OUT/auto_bridge.log"; exit 1; }
poke() { echo "$1" > /tmp/mega-ctl; }

# Latest /r2/auto_mode (latched), as true/false
auto_state() {
    timeout -s INT -k 2 10 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable \
        --field data /r2/auto_mode 2>/dev/null | head -1 | tr 'A-Z' 'a-z'    # True -> true
}
auto_reason() {
    timeout -s INT -k 2 10 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable \
        --field data /r2/auto_mode/reason 2>/dev/null | head -1
}
wait_state() {    # wait_state true|false [reason]
    for _ in $(seq 20); do
        s=$(auto_state)
        if [ "$s" = "$1" ] && { [ -z "$2" ] || [ "$(auto_reason)" = "$2" ]; }; then return 0; fi
        sleep 0.5
    done
    return 1
}
drive() {         # drive <seconds> <m/s>
    timeout -s INT -k 2 "$1" ros2 topic pub -r 15 /foot/cmd_vel geometry_msgs/msg/Twist "{linear: {x: $2}}" \
        > /dev/null 2>&1
    sleep 0.5
}
mark() { wc -l < "$LOG"; }
since() { tail -n +"$(( $1 + 1 ))" "$LOG"; }    # log lines after a mark

echo "== 1. starts off"
wait_state false || fail "1: /r2/auto_mode is not false at start"

echo "== 2. mode off: cmd_vel does not reach the feet"
m=$(mark); drive 2 0.4
since $m | grep -q "ROS:FOOT:" && fail "2: ROS:FOOT: sent with the mode off"

echo "== 3. PS + L2: the Pi drives the feet"
poke button
wait_state true || fail "3: mode did not turn on"
m=$(mark); drive 4 0.4
# Rate from the log's own timestamps (ros2 topic pub takes a while to start)
rate=$(since $m | grep "ROS:FOOT:20,0" | awk 'NR==1{t0=$1} {t=$1; n++} END{if (n>1) printf "%.1f", (n-1)/(t-t0); else print 0}')
echo "   ROS:FOOT:20,0 at $rate per second"
awk -v r="$rate" 'BEGIN{exit !(r >= 12 && r <= 18)}' || fail "3: expected ~15 ROS:FOOT:20,0 per second, got $rate"

echo "== 4. cmd_vel stops: one stop, then silence"
stops=$(since $m | grep -c "ROS:FOOT:0,0")
[ "$stops" -eq 1 ] || fail "4: expected exactly one ROS:FOOT:0,0, got $stops"
m=$(mark); sleep 1
since $m | grep -q "ROS:FOOT:" && fail "4: still sending after the stop"

echo "== 5. stick: off, and cmd_vel no longer reaches the feet"
poke stick
wait_state false stick || fail "5: mode not off with reason stick"
m=$(mark); drive 2 0.4
since $m | grep -q "ROS:FOOT:" && fail "5: ROS:FOOT: sent after the stick"

echo "== 6. the Pi switches it off (service)"
poke button
wait_state true || fail "6: mode did not turn on again"
m=$(mark)
timeout -s INT -k 2 15 ros2 service call /r2/auto_mode/disable std_srvs/srv/Trigger > /dev/null 2>&1 \
    || fail "6: service call failed"
since $m | grep -q "ROS:AUTO:0" || fail "6: ROS:AUTO:0 not sent"
wait_state false pi || fail "6: mode not off with reason pi"

echo "== 7. the Mega restarts with the mode on"
poke button
wait_state true || fail "7: mode did not turn on again"
poke reset
wait_state false boot || fail "7: mode not off with reason boot after a reset"
m=$(mark); drive 2 0.4
since $m | grep -q "ROS:FOOT:" && fail "7: ROS:FOOT: sent after the reset"

if [ -n "$VIDEO" ]; then
    echo "== 8. dome tracker only in autonomous mode (camera: $VIDEO)"
    cat > /tmp/cameras.yaml <<EOF
front:
  source: $VIDEO
  fps: 30
  fourcc: ""
  frame_id: dome_camera_front
EOF
    ros2 launch r2_camera cameras.launch.py config:=/tmp/cameras.yaml > "$OUT/auto_camera.log" 2>&1 &
    CAM=$!
    ros2 launch r2_vision face_detectors.launch.py > "$OUT/auto_faces.log" 2>&1 &
    FACES=$!
    ros2 run r2_dome_tracker dome_tracker --ros-args \
        --params-file "$(ros2 pkg prefix r2_dome_tracker)/share/r2_dome_tracker/config/dome_tracker.yaml" \
        > "$OUT/auto_tracker.log" 2>&1 &
    TRACKER=$!
    trap 'kill $TRACKER $FACES $CAM 2>/dev/null; cleanup' EXIT
    sleep 8
    nonzero() {   # nonzero <seconds>: /dome/speed_cmd messages that are not 0
        timeout -s INT -k 2 "$1" ros2 topic echo --csv /dome/speed_cmd 2>/dev/null | grep -cv '^0$'
    }
    n=$(nonzero 10); echo "   mode off: $n dome speeds"
    [ "$n" -eq 0 ] || fail "8: the tracker moves the dome with the mode off"
    poke button
    wait_state true || fail "8: mode did not turn on"
    m=$(mark)
    n=$(nonzero 10); echo "   mode on: $n dome speeds"
    [ "$n" -gt 10 ] || fail "8: the tracker does not follow the face with the mode on"
    since $m | grep -q "ROS:DOME:[1-9-]" || fail "8: no ROS:DOME: reached the Mega"
    poke stick
    wait_state false stick || fail "8: mode not off"
    sleep 1
    n=$(nonzero 10); echo "   mode off again: $n dome speeds"
    [ "$n" -eq 0 ] || fail "8: the tracker keeps moving the dome after the stick"
fi

echo "ALL PASS"
