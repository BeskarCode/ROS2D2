#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Build the Pico firmware with the git commit of this folder in it (the Pico says it in its
# HELLO answer, and the web console compares it with GitHub). Leaves build/r2_pico_sensors.ino.uf2.
#
#   firmware/r2_pico_sensors/build.sh                  as fast as it can
#   firmware/r2_pico_sensors/build.sh --jobs 2 --nice  gently (on the Pi, while R2 runs)
#
# Needs arduino-cli with the rp2040:rp2040 core and the VL53L0X library (README.md).
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
JOBS=0
NICE=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --jobs) JOBS=$2; shift 2 ;;
    --nice) NICE=(nice -n 19); shift ;;
    *) echo "build.sh: unknown option $1" >&2; exit 2 ;;
  esac
done

COMMIT=unknown
if git -C "$HERE" rev-parse >/dev/null 2>&1; then
  COMMIT=$(git -C "$HERE" log -1 --format=%h -- . 2>/dev/null || true)
  [[ -z $COMMIT ]] && COMMIT=unknown
  [[ -n $(git -C "$HERE" status --porcelain -- . 2>/dev/null) ]] && COMMIT="$COMMIT-dirty"
fi
echo "build: r2_pico_sensors commit $COMMIT"

ARDUINO_CLI=${ARDUINO_CLI:-arduino-cli}
"${NICE[@]}" "$ARDUINO_CLI" compile --fqbn rp2040:rp2040:rpipico2 --jobs "$JOBS" \
  --build-property "compiler.cpp.extra_flags=-DFW_COMMIT=\"$COMMIT\"" \
  --output-dir "$HERE/build" "$HERE"
