#!/usr/bin/env bash
# Build the workspace the way the course expects.
#
#     ./scripts/build.sh                 # build everything
#     ./scripts/build.sh ros2_basics_py  # build one package and its deps
#
# --symlink-install means edits to Python files take effect without rebuilding.
# You still have to rebuild after adding a new entry point, launch file,
# config file, or any change to the interfaces package.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [ -z "${ROS_DISTRO:-}" ]; then
    echo "ROS 2 is not sourced. Run: source /opt/ros/humble/setup.bash" >&2
    exit 1
fi

if [ "$#" -gt 0 ]; then
    colcon build --symlink-install --packages-up-to "$@"
else
    colcon build --symlink-install
fi

echo
echo "Build finished. Now run:"
echo "    source install/setup.bash"
