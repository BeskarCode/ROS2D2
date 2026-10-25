"""The list of cameras, shared by the camera launch, the face detectors and the dome tracker.

cameras.yaml either names the cameras one by one:

    cam1:
      source: /dev/v4l/by-id/usb-...-video-index0
      yaw_deg: -30        # where it points: degrees from the dome's front, + = right
      hfov_deg: 60        # horizontal field of view
      width: 640 ...      # anything else goes to the camera node as parameters

or asks for them to be found:

    auto:
      hfov_deg: 60        # field of view of each camera
      spread_deg: 60      # angle between the first and the last camera
      width: 640 ...      # anything else is copied to every camera

With `auto`, every USB camera plugged in becomes cam1, cam2... ordered by the USB port it
is plugged into, so a camera keeps its number as long as it stays in the same port.
The cameras are spread evenly from left to right: one camera looks straight ahead,
two point at -spread/2 and +spread/2.

The web console's camera setup saves its own cameras.yaml in ~/.config/ros2d2/; when
that file exists it is used instead of the package's one (see config_path).
"""

import glob
import os

import yaml

GEOMETRY = ("yaw_deg", "hfov_deg")
BY_PATH = "/dev/v4l/by-path"
USER_CONFIG = os.path.expanduser("~/.config/ros2d2/cameras.yaml")


def config_path(default):
    """The cameras.yaml to use: the one saved from the web console, if any, else default."""
    return USER_CONFIG if os.path.isfile(USER_CONFIG) else default


def usb_cameras(root=BY_PATH):
    """Stable paths of the USB cameras plugged in, ordered by USB port.

    Each camera has several entries in /dev/v4l/by-path: index0 is the picture (index1 is
    metadata), and the Pi lists every camera twice (usb- and usbv2-). Keep one per device.
    """
    seen, out = set(), []
    for path in sorted(glob.glob(os.path.join(root, "*usb-*video-index0"))):
        dev = os.path.realpath(path)
        if dev not in seen:
            seen.add(dev)
            out.append(path)
    return out


def spread(n, spread_deg):
    """Yaw of n cameras spread evenly over spread_deg, left to right."""
    if n == 1:
        return [0.0]
    return [-spread_deg / 2 + i * spread_deg / (n - 1) for i in range(n)]


def load_cameras(path, found=None):
    """{name: params} in order; params include yaw_deg and hfov_deg.

    found: the auto-detected camera paths (for tests); None = look in /dev/v4l.
    """
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if "auto" in cfg:
        auto = dict(cfg["auto"] or {})
        hfov = float(auto.pop("hfov_deg", 60.0))
        total = float(auto.pop("spread_deg", hfov))
        sources = usb_cameras() if found is None else found
        return {f"cam{i + 1}": {**auto, "source": src, "yaw_deg": yaw, "hfov_deg": hfov}
                for i, (src, yaw) in enumerate(zip(sources, spread(len(sources), total)))}
    out = {}
    for name, params in cfg.items():
        params = dict(params or {})
        params.setdefault("yaw_deg", 0.0)
        params.setdefault("hfov_deg", 60.0)
        out[name] = params
    return out


def node_params(params):
    """The camera node's own parameters (without the geometry the tracker uses)."""
    out = {k: v for k, v in params.items() if k not in GEOMETRY}
    if "source" in out:
        out["source"] = str(out["source"])   # `source: 0` in YAML is an int
    return out
