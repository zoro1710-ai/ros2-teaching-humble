#!/usr/bin/env python3
"""Lesson 12 - launching a small TF tree.

Run it with:
    ros2 launch ros2_basics_py tf_demo.launch.py

    ros2 run tf2_tools view_frames
    ros2 run tf2_ros tf2_echo odom laser
    rviz2       # set Fixed Frame to "odom" and add a TF display

Starts three nodes at once:
    tf_broadcaster        odom -> base_link   (moving, 20 Hz)
    static_tf_broadcaster base_link -> laser  (fixed, published once)
    tf_listener           asks for odom -> laser, which TF2 composes for it
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    dynamic_broadcaster = Node(
        package='ros2_basics_py',
        executable='tf_broadcaster',
        name='tf_broadcaster',
        output='screen',
    )

    static_broadcaster = Node(
        package='ros2_basics_py',
        executable='static_tf_broadcaster',
        name='static_tf_broadcaster',
        output='screen',
    )

    listener = Node(
        package='ros2_basics_py',
        executable='tf_listener',
        name='tf_listener',
        output='screen',
        parameters=[{
            'target_frame': 'odom',
            'source_frame': 'laser',
        }],
    )

    return LaunchDescription([dynamic_broadcaster, static_broadcaster, listener])
