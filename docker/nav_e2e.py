"""End-to-end check of the navigation simulator (run by nav_bench.sh, with the sim running).

1. PS + L2 on the fake Mega -> autonomous mode on, and its sound reaches the Mega
2. a goal across the room -> R2 gets there
3. a goal it cannot reach (behind a wall) -> it gives up, plays its sound and stays still
Prints PASS/FAIL per step and ALL PASS at the end (exit 1 on the first failure).
"""
import json
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, String

rclpy.init()
n = rclpy.create_node("nav_e2e")
seen = {"tx": [], "log": [], "auto": False, "state": {}, "pose": None, "world": None}
latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
n.create_subscription(String, "/mega/tx", lambda m: seen["tx"].append(m.data), 100)
n.create_subscription(String, "/mega/log", lambda m: seen["log"].append(m.data), 100)
n.create_subscription(Bool, "/r2/auto_mode", lambda m: seen.update(auto=m.data), latched)
n.create_subscription(String, "/nav/state", lambda m: seen.update(state=json.loads(m.data)), 10)
n.create_subscription(Odometry, "/odom", lambda m: seen.update(pose=(m.pose.pose.position.x, m.pose.pose.position.y)), 10)
n.create_subscription(String, "/sim/world", lambda m: seen.update(world=m.data), latched)
cmd = n.create_publisher(String, "/sim/world_cmd", 10)
goal = n.create_publisher(PoseStamped, "/nav/goal", 10)


def wait(cond, sec):
    end = time.time() + sec
    while time.time() < end:
        rclpy.spin_once(n, timeout_sec=0.1)
        if cond():
            return True
    return False


def step(name, ok):
    print(("PASS " if ok else "FAIL ") + name, flush=True)
    if not ok:
        print("  last state:", seen["state"], "pose:", seen["pose"], "tx:", seen["tx"][-5:], flush=True)
        sys.exit(1)


def send_goal(x, y):
    g = PoseStamped()
    g.header.frame_id = "odom"
    g.pose.position.x, g.pose.position.y = x, y
    goal.publish(g)


step("simulation running", wait(lambda: seen["world"] and seen["pose"] and seen["state"], 30))
# the fake Mega answers the bridge's ROS:AUTO:? once it is up (slow on a busy Pi)
step("fake Mega answering the bridge", wait(lambda: any("AUTO OFF" in t for t in seen["log"]), 60))
cmd.publish(String(data=json.dumps({"op": "reset"})))
cmd.publish(String(data=json.dumps({"op": "press", "what": "button"})))
step("autonomous mode on (PS + L2)", wait(lambda: seen["auto"], 10))
step("its sound sent to the Mega (S1:$11)", wait(lambda: any("S1:$11" in t for t in seen["tx"]), 5))

# a room with a clear way round: without the person (id 4) the gaps are wider than the
# safety circle needs (1.1 m with the default 0.55 m radius)
cmd.publish(String(data=json.dumps({"op": "remove", "id": 4})))
wait(lambda: False, 0.5)
t0 = time.time()
send_goal(2.2, 1.2)
step("goal across the room reached", wait(lambda: seen["state"].get("state") == "arrived", 90))
print(f"  took {time.time() - t0:.0f} s", flush=True)
step("its sound sent (S1:$W)", wait(lambda: any("S1:$W" in t for t in seen["tx"]), 5))

cmd.publish(String(data=json.dumps({"op": "reset"})))   # back to the full room (R2 back at its start)
wait(lambda: False, 1.0)
t0 = time.time()
send_goal(-3.4, -1.2)
step("impossible goal: gave up", wait(lambda: seen["state"].get("state") == "gave up", 200))
print(f"  took {time.time() - t0:.0f} s", flush=True)
step("its sound sent (S1:$41)", wait(lambda: any("S1:$41" in t for t in seen["tx"]), 5))
wait(lambda: False, 1.5)          # the feet ramp down smoothly after the stop: let them finish
p0 = seen["pose"]
wait(lambda: False, 10)
p1 = seen["pose"]
step("stays still after giving up", abs(p1[0] - p0[0]) < 0.02 and abs(p1[1] - p0[1]) < 0.02)
cmd.publish(String(data=json.dumps({"op": "press", "what": "stick"})))
wait(lambda: False, 1)
print("ALL PASS", flush=True)
