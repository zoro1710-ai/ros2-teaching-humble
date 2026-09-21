#!/usr/bin/env python3
"""Lesson 08 - launching a client/server pair that must agree on names.

Run it with:
    ros2 launch ros2_basics_py led_battery.launch.py

    ros2 topic echo /led_states
    ros2 service list

Both nodes are remapped onto /panel/set_led. Remap the server and forget the
client and nothing happens at all - no error, just silence. That failure mode
is why "ros2 service list" and "ros2 node info" are the first things to check
when a launch file does not behave.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    led_panel = Node(
        package='ros2_basics_py',
        executable='led_panel',
        name='led_panel',
        output='screen',
        parameters=[{'led_count': 4}],
        remappings=[('set_led', 'panel/set_led')],
    )

    battery = Node(
        package='ros2_basics_py',
        executable='battery_node',
        name='battery_node',
        output='screen',
        parameters=[{
            'discharge_time': 4.0,
            'charge_time': 6.0,
            'led_number': 2,
        }],
        remappings=[('set_led', 'panel/set_led')],
    )

    return LaunchDescription([led_panel, battery])
