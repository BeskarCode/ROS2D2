#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Once, on the Pi: what the web console needs to build and flash the Pico firmware itself
# (Setup -> System -> Pico firmware). Safe to run again.
#
#   setup/install_pico_toolchain.sh          (as the user that runs ROS2D2, not root)
#
# - arduino-cli in ~/.local/bin, with the Pico core and the libraries the firmware uses
#   (a few hundred MB in ~/.arduino15 and ~/Arduino)
# - ~/ros2d2-firmware: a copy of the GitHub repo with only firmware/ (git pull brings new ones)
# - /usr/local/sbin/r2-pico-flash: the one root script that copies the built firmware onto the
#   Pico's USB drive, and a sudoers rule that lets this user run it, and nothing else
set -euo pipefail

ARDUINO_CLI_VERSION=1.5.1
CORE=rp2040:rp2040@6.3.1
LIBS=("VL53L0X@1.3.1" "Adafruit GFX Library@1.13.0")
REPO=https://github.com/BeskarCode/ROS2D2
CLONE=$HOME/ros2d2-firmware
HERE=$(cd "$(dirname "$0")" && pwd)
ME=$(id -un)
[[ $ME == root ]] && { echo "run it as the user that runs ROS2D2, not root" >&2; exit 1; }

case $(uname -m) in
  aarch64) ARCH=ARM64 ;;
  x86_64) ARCH=64bit ;;
  *) echo "no arduino-cli for $(uname -m)" >&2; exit 1 ;;
esac

mkdir -p "$HOME/.local/bin"
CLI=$HOME/.local/bin/arduino-cli
if ! "$CLI" version 2>/dev/null | grep -q "Version: $ARDUINO_CLI_VERSION"; then
  echo "== arduino-cli $ARDUINO_CLI_VERSION"
  TMP=$(mktemp -d)
  curl -fsSL -o "$TMP/cli.tar.gz" \
    "https://github.com/arduino/arduino-cli/releases/download/v$ARDUINO_CLI_VERSION/arduino-cli_${ARDUINO_CLI_VERSION}_Linux_$ARCH.tar.gz"
  tar -xzf "$TMP/cli.tar.gz" -C "$TMP" arduino-cli
  install -m 0755 "$TMP/arduino-cli" "$CLI"
  rm -rf "$TMP"
fi

echo "== Pico core and libraries"
"$CLI" config init --overwrite >/dev/null
"$CLI" config add board_manager.additional_urls \
  https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
"$CLI" core update-index
"$CLI" core install "$CORE"
for lib in "${LIBS[@]}"; do "$CLI" lib install "$lib"; done

echo "== $CLONE (only firmware/)"
if [[ ! -d $CLONE/.git ]]; then
  git clone --filter=blob:none --sparse "$REPO" "$CLONE"
  git -C "$CLONE" sparse-checkout set firmware
else
  git -C "$CLONE" pull --ff-only
fi

echo "== /usr/local/sbin/r2-pico-flash and its sudoers rule (asks for your password if needed)"
sudo install -o root -g root -m 0755 "$HERE/r2-pico-flash" /usr/local/sbin/r2-pico-flash
RULE=$(mktemp)
echo "$ME ALL=(root) NOPASSWD: /usr/local/sbin/r2-pico-flash \"\"" > "$RULE"   # "" = no arguments allowed
sudo visudo -cf "$RULE" >/dev/null
sudo install -o root -g root -m 0440 "$RULE" /etc/sudoers.d/r2-pico-flash
rm -f "$RULE"

BUILD=$CLONE/firmware/r2_pico_sensors/build.sh
if [[ -x $BUILD ]]; then
  echo "== a first build (checks it all works)"
  ARDUINO_CLI="$CLI" "$BUILD" --jobs 2 --nice
  echo "Done. The console's System tab can now check for and flash new Pico firmware."
else
  echo "Done, but the firmware on GitHub is older than this installer (no build.sh): the console"
  echo "can flash it once the new firmware is on GitHub's main."
fi
