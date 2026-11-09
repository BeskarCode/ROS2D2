# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Which lidar nodes the droid's launch starts, apart from ROS so it can be tested.

With r2d2-lidar.service installed, the RPLIDAR C1's driver is that service's job: udev starts it
when /dev/r2-lidar appears and systemd stops it when it goes, so the lidar comes back on its own
after being unplugged (sllidar_ros2 does not reopen a port that went away). The main launch then
only runs scan_crop, always, so /scan is there the moment the lidar is plugged in.
"""

SERVICE_FILE = "/etc/systemd/system/r2d2-lidar.service"


def lidar_plan(mode, port_exists, service_installed):
    """(driver, crop): driver is "fake", "sllidar" or None; crop says whether to run scan_crop.

    mode is the launch's lidar argument: "auto", "sim" or "off".
    """
    if mode == "sim":
        return "fake", True
    if mode != "auto":
        return None, False
    if service_installed:
        return None, True
    if port_exists:
        return "sllidar", True
    return None, False
