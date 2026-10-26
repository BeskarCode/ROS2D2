"""The main launch only brings the simulation (fake Mega, simulated room) with sim:=true, and
never runs the real Mega bridge at the same time. Needs ROS (runs on the Pi or in Docker)."""
import importlib.util

import pytest

launch = pytest.importorskip("launch")
ament = pytest.importorskip("ament_index_python.packages")


def entities(sim, mega="true"):
    from launch import LaunchContext
    from launch.actions import IncludeLaunchDescription
    from launch_ros.actions import Node

    path = ament.get_package_share_directory("r2_bringup") + "/launch/dome_tracker.launch.py"
    spec = importlib.util.spec_from_file_location("bringup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ctx = LaunchContext()
    ctx.launch_configurations.update({"sim": sim, "mega": mega, "lidar": "auto", "web": "false", "port": "/dev/null"})
    out = []
    for e in mod.generate_launch_description().entities:
        if getattr(e, "condition", None) is not None and not e.condition.evaluate(ctx):
            continue
        if isinstance(e, IncludeLaunchDescription):
            src = e.launch_description_source
            # .location is only filled in once the launch runs; before that, the substitutions
            parts = getattr(src, "_LaunchDescriptionSource__location", None) or [src.location]
            out.append(("include", "".join(p if isinstance(p, str) else p.perform(ctx) for p in parts)))
        elif isinstance(e, Node):
            out.append(("node", e.node_executable))
    return out


def test_launch_without_sim_has_no_fake_mega():
    ents = entities("false")
    assert not any(kind == "include" and str(loc).endswith("sim.launch.py") for kind, loc in ents)
    assert ("node", "mega_bridge") in ents


def test_launch_with_sim_has_no_real_bridge():
    ents = entities("true")
    assert any(kind == "include" and str(loc).endswith("sim.launch.py") for kind, loc in ents)
    assert ("node", "mega_bridge") not in ents
