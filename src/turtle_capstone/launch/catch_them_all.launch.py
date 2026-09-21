#!/usr/bin/env python3
"""Capstone - start the whole game with one command.

Run it with:
    ros2 launch turtle_capstone catch_them_all.launch.py
    ros2 launch turtle_capstone catch_them_all.launch.py catch_closest_first:=false

Three nodes are started:
    turtlesim_node    the simulator window
    turtle_spawner    creates turtles and removes caught ones
    turtle_controller chases them

All tunable numbers live in config/catch_them_all.yaml so the behaviour can be
changed without touching any code.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('turtle_capstone'),
        'config',
        'catch_them_all.yaml')

    closest_arg = DeclareLaunchArgument(
        'catch_closest_first',
        default_value='true',
        description='true: chase the nearest turtle. false: chase the oldest one.')

    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )

    spawner = Node(
        package='turtle_capstone',
        executable='turtle_spawner',
        name='turtle_spawner',
        output='screen',
        parameters=[config],
    )

    controller = Node(
        package='turtle_capstone',
        executable='turtle_controller',
        name='turtle_controller',
        output='screen',
        parameters=[
            config,
            # Later entries win, so this CLI argument overrides the YAML value.
            {'catch_closest_first': ParameterValue(
                LaunchConfiguration('catch_closest_first'), value_type=bool)},
        ],
    )

    return LaunchDescription([closest_arg, turtlesim, spawner, controller])
