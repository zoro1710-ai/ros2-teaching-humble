#!/usr/bin/env python3
"""See the Defender in RViz, and move every joint by hand.

Run it with:
    ros2 launch defender_description display.launch.py
    ros2 launch defender_description display.launch.py gui:=false

Three nodes start:
    robot_state_publisher     reads the URDF, listens to /joint_states,
                              publishes the whole TF tree
    joint_state_publisher_gui a window of sliders, one per joint, that
                              publishes /joint_states
    rviz2                     draws it

Only 22 of the 25 moving joints get a slider. The right rocker, the
differential and the right flywheel are "mimic" joints: they follow another
joint, just like the real gears force them to.
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
    package_dir = get_package_share_directory('defender_description')
    urdf_file = os.path.join(package_dir, 'urdf', 'defender.urdf.xacro')
    rviz_config = os.path.join(package_dir, 'config', 'defender.rviz')

    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Open the joint slider window.')

    # Command(...) runs xacro at launch time and captures its output.
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
