#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Odometry bench: the dead reckoning (r2_nav) and the laser odometry (rf2o_laser_odometry, built by
# setup_r2_brain.sh) against the simulator's true pose, while the navigator drives R2 across the room.
# Needs rf2o in the workspace. On the Pi after colcon build, or in the ros2d2-dev container:
#
#   WS=~/r2_ws bash docker/odom_bench.sh
#
# Prints how far and how much each one says R2 moved (sim = the truth).
set -o pipefail
source "$(ls /opt/ros/*/setup.bash | head -1)"
WS=${WS:-$HOME/r2_ws}
source "$WS/install/setup.bash"
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID_BENCH:-78}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-/tmp/odom_bench}
mkdir -p "$OUT"
setsid ros2 launch r2_sim sim.launch.py > "$OUT/sim.log" 2>&1 &
G1=$!
setsid ros2 launch r2_nav nav.launch.py dead_reckoning:=false > "$OUT/nav.log" 2>&1 &
G2=$!
setsid ros2 launch r2_sensors sensors.launch.py lidar:=off > "$OUT/sensors.log" 2>&1 &
G3=$!
# the node calls itself CLaserOdometry2DNode: /** so these parameters reach it
cat > "$OUT/rf2o.yaml" <<'YAML'
/**:
  ros__parameters:
    laser_scan_topic: /scan
    odom_topic: /odom_rf2o
    publish_tf: false
    base_frame_id: base_link
    odom_frame_id: odom
    init_pose_from_topic: ""
    freq: 10.0
YAML
setsid ros2 run rf2o_laser_odometry rf2o_laser_odometry_node --ros-args --params-file "$OUT/rf2o.yaml" > "$OUT/rf2o.log" 2>&1 &
G4=$!
# the dead reckoning under other names: the simulator owns /odom and /tf
setsid ros2 run r2_nav dead_reckoning --ros-args -r /odom:=/odom_dr -r /tf:=/tf_dr > "$OUT/dr.log" 2>&1 &
G5=$!
cleanup() {
  for g in $G1 $G2 $G3 $G4 $G5; do kill -TERM -- -"$g" 2>/dev/null; done
  sleep 3
  for g in $G1 $G2 $G3 $G4 $G5; do kill -KILL -- -"$g" 2>/dev/null; done
  wait 2>/dev/null
}
trap cleanup EXIT
sleep 8
python3 "$HERE/odom_check.py" | tee "$OUT/check.log"
