# A ready-made Ubuntu 22.04 + ROS 2 Humble environment for this course.
#
# Build it once:
#     docker build -t ros2-basics -f docker/Dockerfile .
#
# Then use docker/run.sh, which handles the GUI forwarding needed by
# turtlesim and rviz2.

FROM ros:humble-desktop

ARG USERNAME=ros
ARG UID=1000
ARG GID=1000

# Tools used throughout the course.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-pytest \
        ros-humble-turtlesim \
        ros-humble-rqt-common-plugins \
        ros-humble-tf2-tools \
        ros-humble-rviz2 \
        git \
        nano \
        less \
    && rm -rf /var/lib/apt/lists/*

# Work as a normal user, not root, so files created in the mounted workspace
# keep your own ownership.
RUN groupadd --gid ${GID} ${USERNAME} 2>/dev/null || true \
    && useradd --uid ${UID} --gid ${GID} -m ${USERNAME} 2>/dev/null || true

USER ${USERNAME}
WORKDIR /home/${USERNAME}/ros2_ws

# Source ROS 2 (and the workspace, once it has been built) in every shell.
RUN echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc \
    && echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> ~/.bashrc

CMD ["/bin/bash"]
