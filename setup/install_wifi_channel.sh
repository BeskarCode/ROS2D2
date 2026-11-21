#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Once, on the Pi (after setup_droid_wifi.sh): R2's access point picks the quietest WiFi channel
# (1, 6 or 11) by itself every time it starts, and the web console can show how busy they are and
# move it (Setup -> System -> R2's WiFi). Safe to run again.
#
#   setup/install_wifi_channel.sh          (as the user that runs ROS2D2, not root)
#
# - the iw package (to scan)
# - /usr/local/sbin/r2-wifi-channel, run by hostapd before it starts (a systemd drop-in)
# - a sudoers rule: this user may run r2-wifi-channel survey and restart hostapd, nothing else
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
ME=$(id -un)
[[ $ME != root ]] || { echo "Run it as the user that runs ROS2D2, not root" >&2; exit 1; }

echo "== iw, r2-wifi-channel and hostapd's drop-in (asks for your password if needed)"
command -v iw >/dev/null || sudo apt-get install -y iw
sudo install -o root -g root -m 0755 "$HERE/r2-wifi-channel" /usr/local/sbin/r2-wifi-channel
sudo mkdir -p /etc/systemd/system/hostapd.service.d
printf '[Service]\n# R2: pick the quietest channel (1, 6, 11) before the AP comes up; a failure keeps the old one\nExecStartPre=-/usr/local/sbin/r2-wifi-channel pick\n' |
  sudo tee /etc/systemd/system/hostapd.service.d/r2-channel.conf >/dev/null
sudo systemctl daemon-reload

RULE=$(mktemp)
echo "$ME ALL=(root) NOPASSWD: /usr/local/sbin/r2-wifi-channel survey, /usr/bin/systemctl restart hostapd" > "$RULE"
sudo visudo -cf "$RULE" >/dev/null
sudo install -o root -g root -m 0440 "$RULE" /etc/sudoers.d/r2-wifi-channel
rm -f "$RULE"
echo "Done. The AP picks its channel each time it starts; restart it now with: sudo systemctl restart hostapd"
