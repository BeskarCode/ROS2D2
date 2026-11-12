# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Build the firmware's plain-C pieces on the PC (gcc, or zig through `pip install ziglang`)."""

import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
INCLUDE = os.path.join(HERE, "..", "components", "r2_detect")


def _compiler():
    if shutil.which("gcc"):
        return ["gcc"]
    try:
        import ziglang  # noqa: F401
        return [sys.executable, "-m", "ziglang", "cc"]
    except ImportError:
        pytest.skip("no C compiler (install gcc, or: pip install ziglang)")


def build(outdir, name, sources):
    exe = os.path.join(str(outdir), name + (".exe" if os.name == "nt" else ""))
    cmd = _compiler() + ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-I", INCLUDE, "-o", exe]
    cmd += [os.path.join(HERE, s) for s in sources] + ["-lm"]
    subprocess.run(cmd, check=True)
    return exe


def run(exe, args):
    return subprocess.run([exe] + [str(a) for a in args], check=True, capture_output=True,
                          text=True).stdout
