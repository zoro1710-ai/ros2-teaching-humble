#!/usr/bin/env python3
"""Lesson 21 - watch the gait run, with no simulator at all.

Run it with:
    ros2 launch spider_bot walk.launch.py

Then drive it:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.6}}"

This launch file swaps the slider GUI of display.launch.py for the gait
controller. Everything else is identical, because robot_state_publisher does
not care who publishes /joint_states.

There is no physics here: the body stays at the origin and the legs cycle
underneath it, as if the robot were walking on a treadmill. That is exactly
what you want while you are tuning a gait - no falling over, no contact
forces, no simulator to fight. Gazebo comes in lesson 18.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Start robot_state_publisher, the gait controller and RViz."""
    package_dir = get_package_share_directory('spider_bot')
    urdf_file = os.path.join(package_dir, 'urdf', 'spider_bot.urdf.xacro')
    rviz_config = os.path.join(package_dir, 'config', 'spider_bot.rviz')
    gait_config = os.path.join(package_dir, 'config', 'gait.yaml')

    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Open RViz. Set false when running headless.')

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    gait_controller = Node(
        package='spider_bot',
        executable='gait_controller',
        name='gait_controller',
        output='screen',
        parameters=[gait_config],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        rviz_arg,
        robot_state_publisher,
        gait_controller,
        rviz,
    ])
