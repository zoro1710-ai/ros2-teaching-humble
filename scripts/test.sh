#!/usr/bin/env bash
# Run every test in the workspace and print the failures in full.
#
#     ./scripts/test.sh
#     ./scripts/test.sh ros2_basics_py
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [ -z "${ROS_DISTRO:-}" ]; then
    echo "ROS 2 is not sourced. Run: source /opt/ros/humble/setup.bash" >&2
    exit 1
fi

if [ "$#" -gt 0 ]; then
    colcon test --packages-select "$@"
else
    colcon test
fi

# colcon test always exits 0; colcon test-result is what tells you the truth.
colcon test-result --all --verbose
