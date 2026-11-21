#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Once, on the Pi: lets the web console unplug the lidar's USB in software and plug it back
# (Setup -> Sensors -> lidar -> USB). Safe to run again.
#
#   setup/install_lidar_usb.sh          (as the user that runs ROS2D2, not root)
#
# - /usr/local/sbin/r2-lidar-usb: the one root script that unbinds / binds the lidar's USB device,
#   and a sudoers rule that lets this user run it with on, off or state, and nothing else
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
ME=$(id -un)
[[ $ME != root ]] || { echo "Run it as the user that runs ROS2D2, not root" >&2; exit 1; }

echo "== /usr/local/sbin/r2-lidar-usb and its sudoers rule (asks for your password if needed)"
sudo install -o root -g root -m 0755 "$HERE/r2-lidar-usb" /usr/local/sbin/r2-lidar-usb
RULE=$(mktemp)
for a in on off state; do
  echo "$ME ALL=(root) NOPASSWD: /usr/local/sbin/r2-lidar-usb $a" >> "$RULE"
done
sudo visudo -cf "$RULE" >/dev/null
sudo install -o root -g root -m 0440 "$RULE" /etc/sudoers.d/r2-lidar-usb
rm -f "$RULE"
echo "Done. Setup -> Sensors -> lidar can now disconnect and connect the lidar."
