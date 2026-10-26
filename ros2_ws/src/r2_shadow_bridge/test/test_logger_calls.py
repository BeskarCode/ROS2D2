"""ROS 2 Lyrical removed the logger's warn() alias: a node calling get_logger().warn(...)
crashes exactly when it tries to report a problem (a Mega unplugged, a camera lost...).
Every package must use warning()."""
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[2]      # ros2_ws/src
CALL = re.compile(r"get_logger\(\)\.warn\(")


def test_no_logger_warn_alias():
    bad = [f"{p.relative_to(SRC)}:{i}" for p in SRC.glob("*/*/*.py") if p.parent.name != "test"
           for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if CALL.search(line)]
    assert bad == [], "use get_logger().warning(...): " + ", ".join(bad)
