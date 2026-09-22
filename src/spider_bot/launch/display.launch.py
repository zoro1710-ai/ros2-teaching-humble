#!/usr/bin/env python3
"""Lesson 17 - see the robot model, and move every joint by hand.

Run it with:
    ros2 launch spider_bot display.launch.py

Three nodes start:
    robot_state_publisher     reads the URDF, listens to /joint_states,
                              publishes the whole TF tree
    joint_state_publisher_gui a window of sliders, one per joint, that
                              publishes /joint_states
    rviz2                     draws it

That division of labour is the thing to understand. robot_state_publisher
never decides where the joints are; it only turns joint angles into frames.
Something else has to supply /joint_states - sliders here, the gait
controller in walk.launch.py, ros2_control on a real robot.
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
    """Start robot_state_publisher, the joint sliders and RViz."""
    package_dir = get_package_share_directory('spider_bot')
    urdf_file = os.path.join(package_dir, 'urdf', 'spider_bot.urdf.xacro')
    rviz_config = os.path.join(package_dir, 'config', 'spider_bot.rviz')

    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Open the joint slider window.')

    # Command(...) runs xacro at launch time and captures its output. The
    # value_type=str wrapper is required: without it the parameter is treated
    # as a file path instead of the XML itself.
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('gui')),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
    )

    return LaunchDescription([
        gui_arg,
        robot_state_publisher,
        joint_state_publisher_gui,
        rviz,
    ])
