#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# IMU check without the sensor, inside the ros2d2-dev container:
#
#   docker run --rm -v <ROS2D2>:/r2 ros2d2-dev bash /r2/docker/imu_bench.sh
#
# A fake MPU6050 (docker/fakes/smbus2.py) stands still for 3 s, then turns at
# 10 deg/s. Checks that the gyro offset is removed and that the Madgwick filter's
# heading follows the turn.
set -eo pipefail
source /opt/ros/jazzy/setup.bash

echo "== build"
rm -rf /ws/src && mkdir -p /ws && cp -r /r2/ros2_ws/src /ws/src
cd /ws
colcon build --symlink-install --packages-select r2_imu 2>&1 | tail -2
source install/setup.bash
colcon test --packages-select r2_imu --event-handlers console_direct- >/dev/null 2>&1 || true
colcon test-result --verbose | tail -1

echo "== launch with the fake MPU6050"
PYTHONPATH=/r2/docker/fakes:$PYTHONPATH ros2 launch r2_imu imu.launch.py > /tmp/imu.log 2>&1 &
LAUNCH=$!
sleep 7

echo "== results"
grep -E "found|offset" /tmp/imu.log | sed 's/^.*\] //'
echo "data_raw rate:"; timeout 6 ros2 topic hz /imu/data_raw 2>/dev/null | grep "average rate" | tail -1 || true
echo "gyro z while turning (expect ~0.1745 rad/s = 10 deg/s):"
timeout 15 ros2 topic echo --once --field angular_velocity.z /imu/data_raw 2>/dev/null | head -1 || true
echo "tilt (expect 0):"
timeout 15 ros2 topic echo --once --field data /imu/tilt 2>/dev/null | head -1 || true

# How fast the filter's heading turns, from the message stamps: should be ~10 deg/s
echo "heading rate from /imu/data (expect ~10 deg/s):"
timeout 20 python3 - <<'EOF' || echo "  no /imu/data"
import math, rclpy
from sensor_msgs.msg import Imu
rclpy.init()
node = rclpy.create_node("yaw_check")
seen = []
def on_imu(m):
    q = m.orientation
    yaw = math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2)))
    seen.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, yaw))
node.create_subscription(Imu, "/imu/data", on_imu, 50)
while len(seen) < 300:          # 3 s at 100 Hz
    rclpy.spin_once(node, timeout_sec=1.0)
turned = sum((b[1] - a[1] + 180) % 360 - 180 for a, b in zip(seen, seen[1:]))
print(f"  {turned / (seen[-1][0] - seen[0][0]):.2f} deg/s over {seen[-1][0] - seen[0][0]:.1f} s")
EOF

kill $LAUNCH; wait $LAUNCH 2>/dev/null || true
echo "errors:"; grep -iE "error|traceback" /tmp/imu.log | head -5 || echo "  none"
