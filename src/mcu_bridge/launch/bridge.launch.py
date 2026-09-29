#!/usr/bin/env python3
"""Start the bridge with the settings in config/bridge.yaml.

Run it with:
    ros2 launch mcu_bridge bridge.launch.py                      # pretend board
    ros2 launch mcu_bridge bridge.launch.py port:=/dev/ttyUSB0   # real board

Then drive from a second terminal (teleop needs its own keyboard):
    ros2 run mcu_bridge keyboard_teleop
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('mcu_bridge'),
        'config',
        'bridge.yaml')

    port_arg = DeclareLaunchArgument(
        'port',
        default_value='sim',
        description="Serial device such as /dev/ttyUSB0, or 'sim' for no hardware.")

    bridge = Node(
        package='mcu_bridge',
        executable='mcu_bridge',
        name='mcu_bridge',
        output='screen',
        # Later entries win, so the port argument overrides the YAML value.
        parameters=[config, {'port': LaunchConfiguration('port')}],
    )

    return LaunchDescription([port_arg, bridge])
