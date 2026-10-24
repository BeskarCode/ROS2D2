# ROS2D2 test bench: the same ROS 2 Jazzy as the Raspberry Pi, on any PC with Docker.
# Lets you build and run the nodes with a video file instead of the camera and a
# virtual serial port instead of the Mega.
#
#   docker build -t ros2d2-dev ROS2D2/docker
#   docker run -it --rm -v <path to ROS2D2>:/r2 ros2d2-dev

FROM ros:jazzy-ros-base

RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-vision-msgs \
      python3-serial python3-yaml python3-pytest python3-pip \
      socat \
    && rm -rf /var/lib/apt/lists/*

# YuNet 2023 needs OpenCV >= 4.8 (Ubuntu 24.04 ships 4.6); numpy < 2 keeps ROS's ABI
RUN pip3 install --break-system-packages --no-cache-dir \
      "numpy<2" "opencv-python-headless>=4.10,<4.11"

ENV ROS_DOMAIN_ID=2
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /root/.bashrc \
 && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> /root/.bashrc

WORKDIR /ws
