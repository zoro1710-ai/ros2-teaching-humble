#!/usr/bin/env python3
"""Lesson 08 - the simplest launch file.

Run it with:
    ros2 launch ros2_basics_py talker_listener.launch.py

A launch file is Python that RETURNS a description of what to start; it does
not start anything itself. Everything you want to launch goes inside the
LaunchDescription list.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    talker = Node(
        package='ros2_basics_py',
        executable='talker',
        name='talker',
        output='screen',
    )

    listener = Node(
        package='ros2_basics_py',
        executable='listener',
        name='listener',
        output='screen',
    )

    return LaunchDescription([talker, listener])
