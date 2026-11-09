#!/usr/bin/env bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#
# Fixed names for the droid's USB serial devices (/dev/r2-mega, /dev/r2-lidar, /dev/r2-pico).
#
#   ./r2-usb-names.sh                      list the USB serial ports: vendor:product, serial, name
#   sudo ./r2-usb-names.sh r2-lidar ttyUSB0
#                                          from now on, the device now on /dev/ttyUSB0 is /dev/r2-lidar
#
# The rule uses the USB serial number when the device has one, so two adapters with the same
# chip (the RPLIDAR C1 and a Mega clone can both be CP210x) still get their own names. Without
# a serial number it falls back to the USB port the device is plugged into: then keep it in
# that port. Rules go to /etc/udev/rules.d/99-r2-<name>.rules (an old one for that name is
# replaced).
set -euo pipefail

NAMES="r2-mega r2-lidar r2-pico"

prop() { udevadm info -q property -n "$1" 2>/dev/null | sed -n "s/^$2=//p" | head -1; }

list() {
  local found=0
  printf '%-10s %-10s %-26s %-36s %s\n' DEVICE "VID:PID" SERIAL PRODUCT "NOW CALLED"
  for dev in /dev/ttyUSB* /dev/ttyACM*; do
    [[ -e "$dev" ]] || continue
    found=1
    local links
    links=$(for n in $NAMES; do [[ "$(readlink -f "/dev/$n" 2>/dev/null)" == "$(readlink -f "$dev")" ]] && printf '%s ' "/dev/$n"; done)
    printf '%-10s %-10s %-26s %-36s %s\n' "${dev#/dev/}" "$(prop "$dev" ID_VENDOR_ID):$(prop "$dev" ID_MODEL_ID)" \
      "$(prop "$dev" ID_SERIAL_SHORT)" "$(prop "$dev" ID_MODEL)" "${links:--}"
  done
  [[ $found == 1 ]] || echo "No USB serial ports. Is the device plugged in?"
}

assign() {
  local name=$1 tty=${2#/dev/}
  [[ " $NAMES " == *" $name "* ]] || { echo "Name must be one of: $NAMES" >&2; exit 2; }
  [[ -e "/dev/$tty" ]] || { echo "/dev/$tty does not exist (run without arguments to list the ports)" >&2; exit 2; }
  [[ $EUID -eq 0 ]] || { echo "Writing the rule needs root: sudo $0 $*" >&2; exit 2; }
  local vid pid serial path rule
  vid=$(prop "/dev/$tty" ID_VENDOR_ID)
  pid=$(prop "/dev/$tty" ID_MODEL_ID)
  serial=$(prop "/dev/$tty" ID_SERIAL_SHORT)
  path=$(prop "/dev/$tty" ID_PATH)
  # the lidar's driver is a service that follows it being plugged in and out (r2d2-lidar.service)
  local extra=""
  [[ $name == r2-lidar ]] && extra=', TAG+="systemd", ENV{SYSTEMD_WANTS}+="r2d2-lidar.service"'
  if [[ -n "$serial" ]]; then
    rule="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"$vid\", ATTRS{idProduct}==\"$pid\", ATTRS{serial}==\"$serial\", SYMLINK+=\"$name\"$extra"
  elif [[ -n "$path" ]]; then
    rule="SUBSYSTEM==\"tty\", ENV{ID_PATH}==\"$path\", SYMLINK+=\"$name\"$extra"
    echo "No USB serial number: the name follows the USB port ($path). Keep the device in that port."
  else
    echo "Cannot tell /dev/$tty apart (no serial number, no port path)." >&2
    exit 1
  fi
  printf '# Written by r2-usb-names.sh on %s\n%s\n' "$(date -I)" "$rule" > "/etc/udev/rules.d/99-$name.rules"
  udevadm control --reload-rules
  udevadm trigger --subsystem-match=tty
  sleep 1
  echo "/etc/udev/rules.d/99-$name.rules:"
  echo "  $rule"
  if [[ "$(readlink -f "/dev/$name" 2>/dev/null)" == "$(readlink -f "/dev/$tty")" ]]; then
    echo "OK: /dev/$name -> /dev/$tty"
  else
    echo "The rule is written but /dev/$name does not point to /dev/$tty yet: unplug and plug the device again."
  fi
}

case $# in
  0) list ;;
  2) assign "$1" "$2" ;;
  *) sed -n '4,14p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
