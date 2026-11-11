#!/bin/bash
# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# Copy the ROS 2 packages from this computer to the Pi, rebuild them there and write
# ~/r2_ws/VERSION (the commit, its date and whether there were changes not committed), which
# the web console shows in System.
#
#   PI=<your-user>@<pi-address> setup/deploy.sh              every package
#   PI=<your-user>@<pi-address> setup/deploy.sh r2_web r2_nav only these
#
# The Pi's ~/r2_ws is built with --symlink-install, so a running r2d2 service picks up web
# files at once; restart it (sudo systemctl restart r2d2) for Python and launch changes.
set -euo pipefail

PI=${PI:-}
if [[ -z "$PI" ]]; then
  echo "Tell me where the Pi is: PI=<your-user>@<pi-address> $0 [package ...]" >&2
  exit 1
fi
KEY=${KEY:-$HOME/.ssh/r2pi_ed25519}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=$ROOT/ros2_ws/src
cd "$SRC"
if [[ $# -gt 0 ]]; then PKGS=("$@"); else PKGS=($(ls -d */ | tr -d /)); fi
for p in "${PKGS[@]}"; do [[ -d $p ]] || { echo "no package $p in ros2_ws/src" >&2; exit 1; }; done

COMMIT=$(git -C "$ROOT" log -1 --format=%h)
DATE=$(git -C "$ROOT" log -1 --format=%cI)
DIRTY=0
[[ -n $(git -C "$ROOT" status --porcelain -- ros2_ws/src) ]] && DIRTY=1

echo "deploy: ${PKGS[*]} ($COMMIT$([[ $DIRTY == 1 ]] && echo ' + local changes'))"
tar --exclude=__pycache__ -cf - "${PKGS[@]}" | ssh -i "$KEY" "$PI" 'tar -xf - -C ~/r2_ws/src'
ssh -i "$KEY" "$PI" "source /opt/ros/*/setup.bash && cd ~/r2_ws && \
  colcon build --symlink-install --packages-select ${PKGS[*]} > /tmp/r2-deploy-build.log 2>&1 \
    || { tail -30 /tmp/r2-deploy-build.log; exit 1; }; \
  printf 'commit=%s\ndate=%s\ndirty=%s\n' '$COMMIT' '$DATE' '$DIRTY' > ~/r2_ws/VERSION"
echo "deploy: done; ~/r2_ws/VERSION = $COMMIT"
