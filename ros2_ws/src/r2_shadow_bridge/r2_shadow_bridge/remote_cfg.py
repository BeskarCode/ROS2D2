# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""remote.yaml: the settings of the console's virtual Navs (the Remote window and the phone view),
and the two rules the Mega bridge applies to them. No ROS here: test/test_remote_cfg.py.

    stick_limit_pct: 20     # 15..100: how far the virtual Navs' sticks may go (a real Nav is not touched)
    guest: false            # the phone shows only the actions and STOP
    favorites:              # the phone's favourite actions, top of its Actions tab
      - {combo: FOOT_UP_CROSS, name: Vol +}

The one in ~/.config/ros2d2/ (saved from Setup -> Modes) is the one used; with none, or a broken
one, the defaults: a bad file never takes the limit away.
"""

import os

import yaml

from r2_nav.modes import COMBOS

DEFAULTS = {"stick_limit_pct": 20, "guest": False, "favorites": []}
USER_REMOTE = os.path.expanduser("~/.config/ros2d2/remote.yaml")
LIMIT_MIN, LIMIT_MAX = 15, 100   # under 15 % the foot stick stays in ShadowMD's dead zone (+/- 15)
NAME_MAX = 20
FAVORITE_COMBOS = set(COMBOS) | {"DOME_PS_L2"}


class RemoteConfigError(ValueError):
    pass


def parse_remote(text):
    """remote.yaml's text -> its settings, every key filled in. RemoteConfigError says what is wrong."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise RemoteConfigError(f"not valid YAML: {e}") from e
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise RemoteConfigError("remote.yaml must be keys and values")
    unknown = set(data) - set(DEFAULTS)
    if unknown:
        raise RemoteConfigError(f"unknown setting: {', '.join(sorted(unknown))}")
    out = {**DEFAULTS, "favorites": []}
    if "stick_limit_pct" in data:
        v = data["stick_limit_pct"]
        if isinstance(v, bool) or not isinstance(v, int) or not LIMIT_MIN <= v <= LIMIT_MAX:
            raise RemoteConfigError(f"stick_limit_pct must be a whole number from {LIMIT_MIN} to {LIMIT_MAX}")
        out["stick_limit_pct"] = v
    if "guest" in data:
        if not isinstance(data["guest"], bool):
            raise RemoteConfigError("guest must be true or false")
        out["guest"] = data["guest"]
    favs = data.get("favorites") or []
    if not isinstance(favs, list):
        raise RemoteConfigError("favorites must be a list of {combo, name}")
    for f in favs:
        if not isinstance(f, dict) or f.get("combo") not in FAVORITE_COMBOS:
            raise RemoteConfigError(f"favorite with an unknown combo: {f!r}")
        name = f.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= NAME_MAX:
            raise RemoteConfigError(f"each favorite needs a name of 1 to {NAME_MAX} characters")
        out["favorites"].append({"combo": f["combo"], "name": name.strip()})
    return out


def load_remote(path):
    """The settings in path; the defaults if it is missing or broken (never raises)."""
    try:
        with open(path, encoding="utf-8") as f:
            return parse_remote(f.read())
    except (OSError, RemoteConfigError):
        return {**DEFAULTS, "favorites": []}


def limit_stick(v, pct):
    """A stick value (0..255, 128 = centre) kept within pct % of its travel. Junk counts as centred."""
    try:
        v = min(255, max(0, int(v)))
    except (TypeError, ValueError):
        return 128
    span = round(127 * pct / 100)
    return 128 + max(-span, min(span, v - 128))


class PadOwner:
    """Which page drives the virtual Navs: the first one that talks keeps them while it keeps
    talking; another one is ignored until the owner has been quiet for hold_s."""

    def __init__(self, hold_s=1.0):
        self.hold_s = hold_s
        self.owner = None
        self._last = None

    def accept(self, client_id, now):
        if self.owner is None or client_id == self.owner or now - self._last > self.hold_s:
            self.owner = client_id
            self._last = now
            return True
        return False

    def expire(self, now):
        """True when the owner has just gone quiet for longer than hold_s (and is dropped)."""
        if self.owner is not None and now - self._last > self.hold_s:
            self.owner = None
            return True
        return False
