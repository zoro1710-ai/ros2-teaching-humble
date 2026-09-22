#!/usr/bin/env python3
"""Lesson 08 - remapping, parameters and namespaces in a launch file.

Run it with:
    ros2 launch ros2_basics_py number_app.launch.py
    ros2 launch ros2_basics_py number_app.launch.py number:=10 frequency:=4.0

Then look at what actually got created:
    ros2 node list
    ros2 topic list
    ros2 topic echo /my_number_count

This launch file shows the three things you will use constantly:

    parameters= : set a node parameter at launch time
    remappings= : wire a node to a topic name it was not written for
    LaunchConfiguration/DeclareLaunchArgument : make the launch file itself
                                                configurable from the CLI
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    number_arg = DeclareLaunchArgument(
        'number',
        default_value='4',
        description='Value the publisher sends on /my_number.')

    frequency_arg = DeclareLaunchArgument(
        'frequency',
        default_value='2.0',
        description='Publishing frequency in Hz.')

    # A LaunchConfiguration is a placeholder that is resolved at launch time,
    # not a Python value. You cannot do arithmetic on it here.
    #
    # Launch arguments always arrive as STRINGS. number_publisher declared
    # 'number' as an int and 'publish_frequency' as a double, so passing the
    # raw LaunchConfiguration would fail with InvalidParameterTypeException.
    # ParameterValue(..., value_type=...) is what performs the conversion.
    number = ParameterValue(LaunchConfiguration('number'), value_type=int)
    frequency = ParameterValue(LaunchConfiguration('frequency'), value_type=float)

    publisher = Node(
        package='ros2_basics_py',
        executable='number_publisher',
        name='my_number_publisher',
        output='screen',
        parameters=[{
            'number': number,
            'publish_frequency': frequency,
        }],
        remappings=[('number', 'my_number')],
    )

    counter = Node(
        package='ros2_basics_py',
        executable='number_counter',
        name='my_number_counter',
        output='screen',
        remappings=[
            ('number', 'my_number'),
            ('number_count', 'my_number_count'),
        ],
    )

    return LaunchDescription([number_arg, frequency_arg, publisher, counter])
