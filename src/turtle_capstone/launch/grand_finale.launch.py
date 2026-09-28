#!/usr/bin/env python3
"""Grand finale - the combined show: nodes, topics, services, params, actions.

Run it with:
    ros2 launch turtle_capstone grand_finale.launch.py

That starts just two nodes:
    turtlesim_node    the simulator window
    mission_control   the action server that runs the whole hunt

Then, in a second terminal, press the button:
    ros2 run turtle_capstone mission_client 5     # catch 5 turtles
    (Ctrl-C in that terminal cancels the mission mid-hunt)

And retune it live, while it runs:
    ros2 param set /mission_control angular_gain 12.0
    rqt_graph                                     # see all five concepts at once
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('turtle_capstone'),
        'config',
        'grand_finale.yaml')

    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )

    mission_control = Node(
        package='turtle_capstone',
        executable='mission_control',
        name='mission_control',
        output='screen',
        parameters=[config],
    )

    return LaunchDescription([turtlesim, mission_control])
