# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""No name used before it exists (pyflakes F821): follow_node died with a NameError the first
time it saw the marker (NAV-1), in a line no other test reached."""
import glob
import os

import pytest

api = pytest.importorskip("pyflakes.api")
from pyflakes import messages  # noqa: E402
from pyflakes.reporter import Reporter  # noqa: E402

PKG = os.path.join(os.path.dirname(__file__), "..", "r2_nav")


class _Collect(Reporter):
    def __init__(self):
        self.found = []

    def flake(self, m):
        if isinstance(m, messages.UndefinedName):
            self.found.append(str(m))

    def unexpectedError(self, filename, msg):
        self.found.append(f"{filename}: {msg}")

    def syntaxError(self, filename, msg, lineno, offset, text):
        self.found.append(f"{filename}:{lineno}: {msg}")


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(PKG, "*.py"))), ids=os.path.basename)
def test_no_undefined_names(path):
    r = _Collect()
    with open(path, encoding="utf-8") as f:
        api.check(f.read(), path, r)
    assert r.found == []
