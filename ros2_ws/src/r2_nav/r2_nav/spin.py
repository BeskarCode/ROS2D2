"""Spin a node with the cheapest executor this ROS has.

rclpy's default executor rebuilds its wait set in Python on every wake-up: with ~16
subscriptions, /odom at 20 Hz, /scan at 10 Hz and a 10 Hz timer that alone took ~20 % of a
Pi 4 core per node with R2 standing still. The EventsExecutor (rclpy.experimental, Jazzy and
later) does that bookkeeping in C++. Falls back to the default one where it is missing.
"""
import rclpy


def make_executor():
    try:
        from rclpy.experimental import EventsExecutor
        return EventsExecutor()
    except ImportError:
        return rclpy.executors.SingleThreadedExecutor()


def spin(node):
    ex = make_executor()
    ex.add_node(node)
    try:
        ex.spin()
    finally:
        ex.shutdown()
