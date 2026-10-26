#!/bin/bash
# Navigation simulator, end to end: the simulated room and fake Mega with the real bridge, the
# navigator, the sensor poses; then docker/nav_e2e.py drives it. On the Pi (after colcon build):
#
#   bash ~/r2_ws/src/../nav_bench.sh            (or copy it anywhere)
#
# or in the ros2d2-dev container like the other benches. Uses ROS_DOMAIN_ID 77 so it does not
# disturb a running r2d2 service. Ends with ALL PASS, or FAIL <step> and exit 1.
set -o pipefail
DISTRO_SETUP=$(ls /opt/ros/*/setup.bash | head -1)
source "$DISTRO_SETUP"
WS=${WS:-$HOME/r2_ws}
source "$WS/install/setup.bash"
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID_BENCH:-77}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-/tmp/nav_bench}
mkdir -p "$OUT"

# each launch in its own process group, so the whole group (launch + its nodes) can be stopped;
# SIGTERM, because background jobs of a non-interactive shell ignore SIGINT
setsid ros2 launch r2_sim sim.launch.py > "$OUT/sim.log" 2>&1 &
SIM=$!
setsid ros2 launch r2_nav nav.launch.py > "$OUT/nav.log" 2>&1 &
NAV=$!
setsid ros2 launch r2_sensors sensors.launch.py lidar:=off > "$OUT/sensors.log" 2>&1 &
SENS=$!
cleanup() {
  for g in $SIM $NAV $SENS; do kill -TERM -- -"$g" 2>/dev/null; done
  sleep 3
  for g in $SIM $NAV $SENS; do kill -KILL -- -"$g" 2>/dev/null; done
  wait 2>/dev/null
}
trap cleanup EXIT
sleep 6

python3 "$HERE/nav_e2e.py" | tee "$OUT/e2e.log"
RESULT=${PIPESTATUS[0]}
echo "== rates"
timeout 6 ros2 topic hz /scan 2>&1 | grep -m1 average | sed 's/^/\/scan /'
timeout 6 ros2 topic hz /nav/state 2>&1 | grep -m1 average | sed 's/^/\/nav\/state /'
uptime
exit $RESULT
