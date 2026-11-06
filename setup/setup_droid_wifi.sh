#!/usr/bin/env bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# ROS2D2 - turns the Pi's built-in WiFi into the droid's own network. Everything
# inside R2 (the dome camera ESP32, a phone or PC with the web console) joins it,
# so the droid works the same at home and at an event, with no router around.
#
# Run once (safe to re-run), connected by cable: the WiFi stops being a client.
#   sudo bash setup_droid_wifi.sh <ssid> <password>
#
# What it does:
#   1. Installs hostapd (the access point)
#   2. wlan0: fixed 10.42.0.1, hands out addresses 10.42.0.10-49 (systemd-networkd)
#   3. eth0 stays a normal DHCP client, for SSH and internet at home
#   4. cloud-init no longer rewrites the network config on boot
# The Pi is r2pi.local on both networks; cameras are r2-domecam1.local (avahi).

set -euo pipefail

SSID="${1:-}"
PASS="${2:-}"
if [[ -z "$SSID" || ${#PASS} -lt 8 ]]; then
  echo "Usage: sudo bash $0 <ssid> <password (8 characters or more)>" >&2
  exit 1
fi
if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash $0 <ssid> <password>" >&2
  exit 1
fi

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

log "hostapd"
apt-get install -y hostapd

log "Network: eth0 DHCP client, wlan0 left to hostapd + networkd"
mkdir -p /etc/cloud/cloud.cfg.d
echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-r2-disable-network-config.cfg
for f in /etc/netplan/*.yaml; do
  [[ -e "$f" && "$f" != /etc/netplan/60-r2.yaml ]] && mv "$f" "$f.r2-disabled"
done
cat > /etc/netplan/60-r2.yaml <<'EOF'
network:
  version: 2
  ethernets:
    eth0: { dhcp4: true, optional: true }
EOF
chmod 600 /etc/netplan/60-r2.yaml

cat > /etc/systemd/network/10-r2-wlan0.network <<'EOF'
[Match]
Name=wlan0

[Network]
Address=10.42.0.1/24
DHCPServer=yes
MulticastDNS=no
ConfigureWithoutCarrier=yes

[DHCPServer]
PoolOffset=10
PoolSize=40
EmitDNS=no
EmitRouter=no
EOF

log "Access point ${SSID}"
cat > /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
country_code=ES
ssid=${SSID}
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=${PASS}
EOF
chmod 600 /etc/hostapd/hostapd.conf

systemctl unmask hostapd
systemctl enable hostapd
netplan apply
systemctl restart systemd-networkd
systemctl restart hostapd
systemctl restart avahi-daemon

log "Done"
ip -br addr show wlan0
systemctl is-active hostapd
