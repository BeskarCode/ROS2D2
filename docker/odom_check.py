# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Run by odom_bench.sh: drives R2 across the simulated room and prints how far and how much the
simulator (the truth), rf2o (/odom_rf2o) and the dead reckoning (/odom_dr) say it moved."""
import json, math, time
import rclpy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, String
rclpy.init(); n = rclpy.create_node("odom_check")
latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
P = {}
def od(name):
    def cb(m):
        q = m.pose.pose.orientation
        P[name] = (m.pose.pose.position.x, m.pose.pose.position.y, math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))
    return cb
for t, k in (("/odom", "sim"), ("/odom_rf2o", "rf2o"), ("/odom_dr", "dr")):
    n.create_subscription(Odometry, t, od(k), 10)
S = {"auto": False, "connected": False, "state": {}}
n.create_subscription(Bool, "/r2/auto_mode", lambda m: S.update(auto=m.data), latched)
n.create_subscription(Bool, "/mega/connected", lambda m: S.update(connected=m.data), latched)
n.create_subscription(String, "/nav/state", lambda m: S.update(state=json.loads(m.data)), 10)
cmd = n.create_publisher(String, "/sim/world_cmd", 10); goal = n.create_publisher(PoseStamped, "/nav/goal", 10)
def wait(c, s):
    e = time.time() + s
    while time.time() < e:
        rclpy.spin_once(n, timeout_sec=0.1)
        if c(): return True
    return False
print("connected", wait(lambda: S["connected"], 60)); wait(lambda: False, 2)
cmd.publish(String(data=json.dumps({"op": "reset"}))); cmd.publish(String(data=json.dumps({"op": "remove", "id": 4})))
cmd.publish(String(data=json.dumps({"op": "press", "what": "button"})))
print("auto", wait(lambda: S["auto"], 10))
print("odom sources", wait(lambda: {"sim", "rf2o", "dr"} <= set(P), 15), sorted(P))
wait(lambda: False, 1)
base = dict(P)
g = PoseStamped(); g.header.frame_id = "odom"; g.pose.position.x, g.pose.position.y = 2.2, 1.2; goal.publish(g)
t0 = time.time(); print("arrived", wait(lambda: S["state"].get("state") == "arrived", 180), round(time.time() - t0), "s; state:", S["state"].get("state"), S["state"].get("why"), "lost:", S["state"].get("lost"), "sources:", S["state"].get("sources"))
wait(lambda: False, 1)
def moved(k):
    a, b = base.get(k), P.get(k)
    return None if a is None or b is None else (round(math.hypot(b[0]-a[0], b[1]-a[1]), 2), round(math.degrees(b[2]-a[2]) % 360))
for k in ("sim", "rf2o", "dr"):
    print(k, "start", tuple(round(v, 2) for v in base.get(k, ())), "end", tuple(round(v, 2) for v in P.get(k, ())), "moved m, deg:", moved(k))
