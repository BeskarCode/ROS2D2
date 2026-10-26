#!/usr/bin/env bash
# ROS2D2 - prepares a Raspberry Pi 4 (Ubuntu Server 24.04 or 26.04, 64-bit) as the
# ROS 2 "brain" that sits on top of a ShadowMD Arduino Mega.
#
# Run once (safe to re-run):
#   sudo bash setup_r2_brain.sh [username]
#
# What it does:
#   1. Updates the system and installs ROS 2 (Jazzy on 24.04, Lyrical on 26.04)
#   2. Installs the packages the brain needs: cameras, image transport,
#      web console bridge (rosbridge), video streaming, serial, audio
#   3. Python venv with a recent OpenCV (YuNet face detector needs >= 4.8)
#   4. Gives the user access to serial / video / audio devices
#   5. udev rule: the Mega always shows up as /dev/r2-mega
#   6. Creates the colcon workspace ~/r2_ws and sources ROS in ~/.bashrc

set -euo pipefail

R2_USER="${1:-${SUDO_USER:-fernando}}"
R2_HOME="$(getent passwd "$R2_USER" | cut -d: -f6)"
ROS_DOMAIN=2   # all R2 nodes share this DDS domain

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash $0" >&2
  exit 1
fi
. /etc/os-release
# Each ROS 2 LTS is built for one Ubuntu LTS
case "${VERSION_ID}" in
  24.04) ROS_DISTRO=jazzy ;;
  26.04) ROS_DISTRO=lyrical ;;
  *) echo "Expected Ubuntu 24.04 or 26.04, found ${PRETTY_NAME}." >&2; exit 1 ;;
esac
echo "Ubuntu ${VERSION_ID} -> ROS 2 ${ROS_DISTRO}"

export DEBIAN_FRONTEND=noninteractive
# On a fresh image unattended-upgrades holds the dpkg lock for several minutes
# after boot: wait for it instead of failing
echo 'DPkg::Lock::Timeout "1800";' > /etc/apt/apt.conf.d/90-r2-lock-timeout

log "Clock"
# The Pi has no RTC; with a wrong date apt rejects the ROS repository signatures.
# Some home routers block the default Ubuntu NTP server, so add alternatives
# and, if still unsynchronised, take the date from an HTTPS response header
# (-k: with a wrong clock the certificate can look not-yet-valid).
# 24.04 uses systemd-timesyncd; 26.04 uses chrony (NTS over TLS, which fails while
# the clock is wrong, hence the plain-NTP servers added here too).
if systemctl list-unit-files chrony.service >/dev/null 2>&1; then
  mkdir -p /etc/chrony/sources.d
  printf 'server %s iburst\n' time.google.com time.cloudflare.com es.pool.ntp.org \
    > /etc/chrony/sources.d/r2-brain.sources
  systemctl restart chrony
  chronyc -a makestep >/dev/null 2>&1 || true
else
  mkdir -p /etc/systemd/timesyncd.conf.d
  cat > /etc/systemd/timesyncd.conf.d/r2-brain.conf <<'EOF'
[Time]
NTP=time.google.com time.cloudflare.com es.pool.ntp.org
FallbackNTP=ntp.ubuntu.com pool.ntp.org
EOF
  systemctl restart systemd-timesyncd
fi
for _ in $(seq 1 15); do
  [[ "$(timedatectl show -p NTPSynchronized --value)" == "yes" ]] && break
  sleep 2
done
if [[ "$(timedatectl show -p NTPSynchronized --value)" != "yes" ]]; then
  HTTP_DATE=$(curl -skI --max-time 10 https://www.google.com | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r')
  if [[ -n "$HTTP_DATE" ]]; then
    date -s "$HTTP_DATE" >/dev/null
    echo "NTP not reachable; clock set from HTTPS header"
  fi
fi
date

log "Ubuntu repositories"
# The Ubuntu Server image for the Pi ships with only "<codename>" and "<codename>-security".
# Without "<codename>-updates", ROS dependencies such as libzstd-dev / liblz4-dev fail:
# the security update of the library is installed but its -dev package is not
# available at the same version ("you have held broken packages").
UBUNTU_SOURCES=/etc/apt/sources.list.d/ubuntu.sources
CN="${VERSION_CODENAME}"
if [[ -f "$UBUNTU_SOURCES" ]] && ! grep -qE "^Suites:.*${CN}-updates" "$UBUNTU_SOURCES"; then
  sed -i -E "s/^Suites: ${CN}\$/Suites: ${CN} ${CN}-updates ${CN}-backports/" "$UBUNTU_SOURCES"
fi
grep -E '^Suites:' "$UBUNTU_SOURCES" || true

log "Locale and base packages"
apt-get update
apt-get install -y locales software-properties-common curl git
locale-gen en_US.UTF-8 es_ES.UTF-8
update-locale LANG=en_US.UTF-8
add-apt-repository -y universe

log "ROS 2 apt source"
if ! dpkg -s ros2-apt-source >/dev/null 2>&1; then
  ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | grep -F '"tag_name"' | awk -F'"' '{print $4}')
  curl -fL -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"
  dpkg -i /tmp/ros2-apt-source.deb
fi

log "System upgrade"
apt-get update
apt-get -y upgrade

log "ROS 2 ${ROS_DISTRO}"
apt-get install -y \
  ros-${ROS_DISTRO}-ros-base \
  ros-dev-tools \
  python3-colcon-common-extensions \
  python3-rosdep

log "Brain packages: cameras, image transport, web bridge, diagnostics"
# (no usb_cam: it has no Lyrical build, and r2_camera reads the webcam with OpenCV)
apt-get install -y \
  ros-${ROS_DISTRO}-v4l2-camera \
  ros-${ROS_DISTRO}-cv-bridge \
  ros-${ROS_DISTRO}-vision-msgs \
  ros-${ROS_DISTRO}-image-transport \
  ros-${ROS_DISTRO}-image-transport-plugins \
  ros-${ROS_DISTRO}-compressed-image-transport \
  ros-${ROS_DISTRO}-rosbridge-suite \
  ros-${ROS_DISTRO}-web-video-server \
  ros-${ROS_DISTRO}-diagnostic-updater \
  ros-${ROS_DISTRO}-rqt-reconfigure \
  ros-${ROS_DISTRO}-foxglove-bridge

log "Sensor packages: IMU filter"
apt-get install -y \
  ros-${ROS_DISTRO}-imu-filter-madgwick

log "System tools: serial, I2C, video, audio"
apt-get install -y \
  python3-serial python3-smbus2 i2c-tools \
  python3-venv python3-pip python3-opencv python3-yaml \
  v4l-utils ffmpeg \
  alsa-utils portaudio19-dev \
  htop tmux avahi-daemon

log "rosdep"
[[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]] || rosdep init
sudo -u "$R2_USER" rosdep update

log "Device access for ${R2_USER}"
getent group i2c >/dev/null || groupadd -r i2c
usermod -aG dialout,video,audio,plugdev,i2c "$R2_USER"
# /dev/i2c-1 for the i2c group (the MPU6050 and the DF2301QG live there)
echo 'KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660"' > /etc/udev/rules.d/99-r2-i2c.rules

log "udev: the Mega appears as /dev/r2-mega"
cat > /etc/udev/rules.d/99-r2-mega.rules <<'EOF'
# Genuine Arduino Mega 2560 (and R3)
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0042", SYMLINK+="r2-mega"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0010", SYMLINK+="r2-mega"
# Mega ADK (the ShadowMD board) and Mega ADK R3
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="003f", SYMLINK+="r2-mega"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0044", SYMLINK+="r2-mega"
# Clones with CH340 / FTDI / CP210x USB-serial chips
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="r2-mega"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="r2-mega"
# TODO when the RPLIDAR C1 arrives: its USB adapter is probably a CP210x too. Check
# with lsusb and give it its own rule (/dev/r2-lidar), by serial number if needed.
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="r2-mega"
EOF
udevadm control --reload-rules
udevadm trigger

log "Python venv with OpenCV for the vision nodes"
VENV="${R2_HOME}/r2-venv"
if [[ ! -d "$VENV" ]]; then
  # system-site-packages so rclpy / cv_bridge from ROS stay visible
  sudo -u "$R2_USER" python3 -m venv --system-site-packages "$VENV"
fi
if [[ "${ROS_DISTRO}" == "jazzy" ]]; then
  # Ubuntu 24.04 ships OpenCV 4.6, too old for YuNet 2023.
  # numpy<2 keeps the ABI that Ubuntu's ROS packages (cv_bridge) were built with
  sudo -u "$R2_USER" "$VENV/bin/pip" install --upgrade pip
  sudo -u "$R2_USER" "$VENV/bin/pip" install "numpy<2" "opencv-contrib-python-headless>=4.10,<4.11"
fi
# Ubuntu 26.04 ships OpenCV 4.10 and numpy 2, the same ones Lyrical was built
# with, so the venv just uses the system packages

log "Workspace ~/r2_ws"
sudo -u "$R2_USER" mkdir -p "${R2_HOME}/r2_ws/src"

log "socat (the navigation simulator joins the real Mega bridge to a fake Mega with a pty pair)"
apt-get install -y socat

log "Lidar driver: Slamtec sllidar_ros2 (RPLIDAR C1), from source"
# No binary package supports the C1 (ros-*-rplidar-ros stops at the A3/S1), so it is
# built with the rest of the workspace: cd ~/r2_ws && colcon build
apt-get install -y build-essential
# Our fork of Slamtec's repo, pinned to a known commit so a reinstall builds the same driver
SLLIDAR="${R2_HOME}/r2_ws/src/sllidar_ros2"
SLLIDAR_REPO="https://github.com/BeskarCode/sllidar_ros2.git"
SLLIDAR_COMMIT="1eeb93039c56f6e78d760e3550132dde315adc23"   # + Lyrical build fix
if [[ ! -d "$SLLIDAR/.git" ]]; then
  sudo -u "$R2_USER" git clone "$SLLIDAR_REPO" "$SLLIDAR"
fi
sudo -u "$R2_USER" git -C "$SLLIDAR" fetch -q origin
sudo -u "$R2_USER" git -C "$SLLIDAR" checkout -q "$SLLIDAR_COMMIT"

log "Shell environment"
BASHRC="${R2_HOME}/.bashrc"
if ! grep -q '# >>> r2-brain >>>' "$BASHRC"; then
  cat >> "$BASHRC" <<EOF

# >>> r2-brain >>>
source /opt/ros/${ROS_DISTRO}/setup.bash
[ -f ~/r2_ws/install/setup.bash ] && source ~/r2_ws/install/setup.bash
export ROS_DOMAIN_ID=${ROS_DOMAIN}
export RCUTILS_COLORIZED_OUTPUT=1
# <<< r2-brain <<<
EOF
  chown "$R2_USER":"$R2_USER" "$BASHRC"
fi

log "ROS2D2 service (starts with the Pi; the web console restarts it)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/r2d2.service" ]]; then
  sed -e "s#@USER@#${R2_USER}#g" -e "s#@HOME@#${R2_HOME}#g" -e "s#@DISTRO@#${ROS_DISTRO}#g"     "$SCRIPT_DIR/r2d2.service" > /etc/systemd/system/r2d2.service
  # (systemd environment files take no comments at the end of a line)
  [[ -f /etc/default/r2d2 ]] || printf '%s
' '# Remove mega:=false once the Mega is plugged in' 'R2D2_ARGS="mega:=false"' > /etc/default/r2d2
  systemctl daemon-reload
  systemctl enable r2d2
  echo "Enabled r2d2.service: it starts once the workspace is built (cd ~/r2_ws && colcon build)"
fi

log "Check"
# ROS's setup.bash reads unset variables: relax "set -u" while sourcing it
set +u
. /opt/ros/${ROS_DISTRO}/setup.bash
set -u
echo "ROS_DISTRO: ${ROS_DISTRO}"
ros2 pkg list | grep -E '^(v4l2_camera|rosbridge_server|web_video_server|cv_bridge)$' || true
sudo -u "$R2_USER" "$VENV/bin/python" -c "import cv2, numpy; print('OpenCV', cv2.__version__, 'numpy', numpy.__version__)"
ls -l /dev/r2-mega 2>/dev/null || echo "Mega not detected (plug it in by USB)"
ls /dev/video* 2>/dev/null || echo "No cameras detected"

log "Done. Log out and back in (or reboot) so the new groups take effect."
