#!/usr/bin/env python3
"""Check that this machine is ready for the course.

Run it from the workspace root, before anything else:

    python3 scripts/verify_setup.py

It checks the things that actually break for beginners, in the order they
break, and tells you the exact command that fixes each one.
"""

import os
import shutil
import subprocess
import sys

EXPECTED_DISTRO = 'humble'
REQUIRED_PACKAGES = [
    'ros2_basics_interfaces',
    'ros2_basics_py',
    'turtle_capstone',
    'spider_bot',
]

# Part 6 needs these to show the robot. Missing ones are a warning, not a
# failure - lessons 00 to 16 do not need them at all.
PART_SIX_PACKAGES = [
    ('xacro', 'xacro', 'builds the robot description (lesson 17)'),
    ('robot_state_publisher', 'robot-state-publisher',
     'turns joint angles into TF (lesson 17)'),
    ('joint_state_publisher_gui', 'joint-state-publisher-gui',
     'the joint sliders (lesson 17)'),
    ('rviz2', 'rviz2', 'draws the robot (lessons 17 and 21)'),
]

PASS = '[ ok ]'
FAIL = '[fail]'
WARN = '[warn]'


def run(command):
    """Run a command and return (returncode, combined output)."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=20, check=False)
    except FileNotFoundError:
        return 127, ''
    except subprocess.TimeoutExpired:
        return 124, ''
    return result.returncode, (result.stdout + result.stderr).strip()


def check_ros_sourced():
    """ROS 2 must be sourced, and it must be the Humble distribution."""
    distro = os.environ.get('ROS_DISTRO')

    if not distro:
        print(FAIL, 'ROS 2 is not sourced in this shell.')
        print('       fix: source /opt/ros/%s/setup.bash' % EXPECTED_DISTRO)
        print('       tip: add that line to ~/.bashrc so it happens every time.')
        return False

    if distro != EXPECTED_DISTRO:
        print(WARN, 'ROS_DISTRO is "%s", this course targets "%s".'
              % (distro, EXPECTED_DISTRO))
        print('       Most things will still work, but commands may differ.')
        return True

    print(PASS, 'ROS 2 %s is sourced.' % distro)
    return True


def check_ros2_cli():
    """The ros2 command itself must be on PATH and runnable."""
    if shutil.which('ros2') is None:
        print(FAIL, 'the "ros2" command was not found.')
        print('       fix: install ROS 2 Humble, see docs/00-install-and-setup.md')
        return False

    code, output = run(['ros2', '--help'])
    if code != 0:
        print(FAIL, 'the "ros2" command failed to run.')
        print('       output:', output.splitlines()[0] if output else '(none)')
        return False

    print(PASS, 'the ros2 CLI works.')
    return True


def check_build_tools():
    """colcon and rosdep are needed to build the workspace."""
    ok = True
    for tool, fix in (
        ('colcon', 'sudo apt install python3-colcon-common-extensions'),
        ('rosdep', 'sudo apt install python3-rosdep'),
    ):
        if shutil.which(tool) is None:
            print(FAIL, '%s is not installed.' % tool)
            print('       fix:', fix)
            ok = False
        else:
            print(PASS, '%s is installed.' % tool)
    return ok


def check_workspace_layout():
    """We must be standing in the root of this repository."""
    if not os.path.isdir('src'):
        print(FAIL, 'no src/ directory here.')
        print('       fix: cd into the repository root and run this again.')
        return False

    missing = [
        name for name in REQUIRED_PACKAGES
        if not os.path.isfile(os.path.join('src', name, 'package.xml'))
    ]

    if missing:
        print(FAIL, 'missing package(s) under src/: %s' % ', '.join(missing))
        return False

    print(PASS, 'all %d course packages are present under src/.' % len(REQUIRED_PACKAGES))
    return True


def check_workspace_built():
    """Warn (not fail) if the workspace has not been built and sourced yet."""
    if not os.path.isdir('install'):
        print(WARN, 'the workspace has not been built yet.')
        print('       fix: colcon build --symlink-install')
        print('       then: source install/setup.bash')
        return True

    code, output = run(['ros2', 'pkg', 'list'])
    if code != 0:
        print(WARN, 'could not list packages, is the workspace sourced?')
        return True

    installed = set(output.split())
    not_found = [name for name in REQUIRED_PACKAGES if name not in installed]

    if not_found:
        print(WARN, 'built, but not visible to ros2: %s' % ', '.join(not_found))
        print('       fix: source install/setup.bash')
    else:
        print(PASS, 'the workspace is built and sourced.')
    return True


def check_turtlesim():
    """turtlesim is needed for the capstone project."""
    code, output = run(['ros2', 'pkg', 'prefix', 'turtlesim'])
    if code != 0:
        print(WARN, 'turtlesim is not installed (only the capstone needs it).')
        print('       fix: sudo apt install ros-%s-turtlesim' % EXPECTED_DISTRO)
        return True

    print(PASS, 'turtlesim is installed.')
    return True


def check_part_six():
    """Part 6 (the legged robot) needs xacro, RViz and friends."""
    missing = []
    for package, apt_name, why in PART_SIX_PACKAGES:
        code, _ = run(['ros2', 'pkg', 'prefix', package])
        if code != 0:
            missing.append((package, apt_name, why))

    if not missing:
        print(PASS, 'Part 6 (spider bot) prerequisites are installed.')
        return True

    print(WARN, '%d Part 6 package(s) missing (lessons 00-16 do not need them):'
          % len(missing))
    for package, _, why in missing:
        print('       %-26s %s' % (package, why))
    print('       fix: sudo apt install %s' % ' '.join(
        'ros-%s-%s' % (EXPECTED_DISTRO, apt_name) for _, apt_name, _ in missing))
    return True


def main():
    """Run every check and report an overall result."""
    print('ROS 2 basics - environment check')
    print('=' * 48)

    checks = [
        check_ros_sourced,
        check_ros2_cli,
        check_build_tools,
        check_workspace_layout,
        check_workspace_built,
        check_turtlesim,
        check_part_six,
    ]

    failed = 0
    for check in checks:
        if not check():
            failed += 1

    print('=' * 48)
    if failed:
        print('%d check(s) failed. Fix the lines marked %s and run this again.'
              % (failed, FAIL))
        return 1

    print('Everything looks good. Start with docs/README.md.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
