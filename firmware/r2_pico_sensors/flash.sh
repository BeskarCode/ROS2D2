#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Build the Pico firmware on this computer and flash it on the Pico plugged into the Pi,
# without touching BOOTSEL: the Pi asks the running firmware to restart into its USB
# loader (1200 baud on its serial port), then copies the .uf2 to the drive that appears.
#
#   firmware/r2_pico_sensors/flash.sh            # PI=fernando@192.168.68.112 by default
#   PI=fernando@r2pi.local firmware/r2_pico_sensors/flash.sh
#
# Needs arduino-cli with the rp2040:rp2040 core and the VL53L0X library (README.md).
# The r2d2 service is stopped while flashing (it holds the port) and started again.
set -euo pipefail

PI=${PI:-fernando@192.168.68.112}
KEY=${KEY:-$HOME/.ssh/r2pi_ed25519}
HERE=$(cd "$(dirname "$0")" && pwd)
UF2=$HERE/build/r2_pico_sensors.ino.uf2

arduino-cli compile --fqbn rp2040:rp2040:rpipico2 --output-dir "$HERE/build" "$HERE"
scp -q -i "$KEY" "$UF2" "$PI:/tmp/r2_pico_sensors.uf2"

ssh -i "$KEY" "$PI" 'bash -s' <<'REMOTE'
set -u
DRIVE=/dev/disk/by-label/RP2350
wait_for() {   # wait_for <path> <seconds>
  for _ in $(seq $(( $2 * 5 ))); do [ -e "$1" ] && return 0; sleep 0.2; done
  return 1
}
fail() { echo "flash: $1" >&2; sudo systemctl start r2d2; exit 1; }

sudo systemctl stop r2d2
if [ ! -e "$DRIVE" ]; then
  [ -e /dev/r2-pico ] || fail "no Pico: neither /dev/r2-pico nor its USB drive"
  stty -F /dev/r2-pico 1200 || fail "could not ask the Pico to restart"
  wait_for "$DRIVE" 10 || fail "the Pico's USB drive did not appear (hold BOOTSEL while plugging it in)"
fi
MNT=$(mktemp -d)
sudo mount "$DRIVE" "$MNT" || fail "could not mount the Pico's drive"
sudo cp /tmp/r2_pico_sensors.uf2 "$MNT/" && sync
sudo umount "$MNT" 2>/dev/null; rmdir "$MNT"
wait_for /dev/r2-pico 10 || fail "the Pico did not come back after flashing"
sleep 1
sudo systemctl start r2d2
echo "flash: done, Pico on /dev/r2-pico"
REMOTE
