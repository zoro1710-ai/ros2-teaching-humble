#!/usr/bin/env python3
"""Lesson 18/19 - the same robot, in a physics simulator.

Run it with:
    ros2 launch spider_bot gazebo.launch.py

Needs Gazebo Classic and the ros2_control bridge:
    sudo apt install ros-humble-gazebo-ros-pkgs \
                     ros-humble-gazebo-ros2-control \
                     ros-humble-ros2-control \
                     ros-humble-ros2-controllers

What is different from walk.launch.py:

    * gazebo provides gravity, contacts and friction, so the robot can fall
      over. It will, at first. That is the point.
    * spawn_entity.py injects the robot into the running simulator using the
      same /robot_description that RViz reads.
    * ros2_control takes over the joints. /joint_states now comes from the
      simulated hardware, not from the gait controller, so the joint angles
      you see are what the robot ACHIEVED, not what you asked for.
    * the gait controller therefore has to send commands instead of states -
      see gait_to_controller.py, and lesson 19.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Start Gazebo, spawn the robot and load the controllers in order."""
    package_dir = get_package_share_directory('spider_bot')
    urdf_file = os.path.join(package_dir, 'urdf', 'spider_bot.urdf.xacro')
    gait_config = os.path.join(package_dir, 'config', 'gait.yaml')

    gazebo_dir = get_package_share_directory('gazebo_ros')

    world_arg = DeclareLaunchArgument(
        'world',
        default_value='empty.world',
        description='Gazebo world file to load.')

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    # Gazebo itself, started from the launch file that ships with gazebo_ros.
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_dir, 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': LaunchConfiguration('world')}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}],
    )

    # Reads /robot_description off the topic and inserts the robot.
    # -z 0.25 drops it in slightly above the ground so the legs are not
    # already intersecting it at t=0.
    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_spider_bot',
        output='screen',
        arguments=['-topic', 'robot_description',
                   '-entity', 'spider_bot',
                   '-z', '0.25'],
    )

    # Controllers must be loaded AFTER the robot exists in the simulator.
    # RegisterEventHandler is how a launch file expresses "then".
    load_joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    load_leg_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['leg_position_controller'],
        output='screen',
    )

    gait_controller = Node(
        package='spider_bot',
        executable='gait_to_controller',
        name='gait_controller',
        output='screen',
        parameters=[gait_config, {'use_sim_time': True}],
    )

    return LaunchDescription([
        world_arg,
        gazebo,
        robot_state_publisher,
        spawn,
        # spawn finishes -> load the broadcaster
        RegisterEventHandler(OnProcessExit(
            target_action=spawn,
            on_exit=[load_joint_state_broadcaster])),
        # broadcaster finishes -> load the position controller
        RegisterEventHandler(OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_leg_controller])),
        # position controller is up -> start walking
        RegisterEventHandler(OnProcessExit(
            target_action=load_leg_controller,
            on_exit=[gait_controller])),
    ])
