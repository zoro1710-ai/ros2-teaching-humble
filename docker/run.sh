#!/usr/bin/env bash
# Start the course container with GUI support (needed for turtlesim/rviz2).
#
#     ./docker/run.sh
#
# The repository is mounted at ~/ros2_ws inside the container, so anything you
# build or edit is visible on both sides.
set -euo pipefail

IMAGE=${IMAGE:-ros2-basics}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Let the container talk to the host X server.
xhost +local:docker >/dev/null 2>&1 || {
    echo "warning: could not run xhost. GUI apps may not open." >&2
}

exec docker run -it --rm \
    --name ros2-basics \
    --net=host \
    --ipc=host \
    -e DISPLAY="${DISPLAY}" \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "${REPO_ROOT}:/home/ros/ros2_ws:rw" \
    "${IMAGE}" "$@"
