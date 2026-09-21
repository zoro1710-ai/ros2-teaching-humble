#!/usr/bin/env python3
"""Lesson 08 - loading parameters from a YAML file.

Run it with:
    ros2 launch ros2_basics_py params_demo.launch.py

    ros2 param list
    ros2 param get /parameter_demo robot_name

Hard-coding parameters in a launch file works, but a YAML file is what you
want as soon as there is more than a handful: it can be edited without
touching code, diffed in review, and swapped per robot.

The YAML layout is significant:

    <node_name>:
      ros__parameters:
        key: value

Use "/**" as the node name to apply the block to every node that loads the
file. If the node name in the YAML does not match the node's actual name
(including any namespace), the parameters are silently ignored - that is the
number one reason a YAML file "does not work".
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Never hard-code an absolute path. get_package_share_directory finds the
    # installed share/ folder of the package, wherever the workspace lives.
    config = os.path.join(
        get_package_share_directory('ros2_basics_py'),
        'config',
        'parameter_demo.yaml')

    parameter_demo = Node(
        package='ros2_basics_py',
        executable='parameter_demo',
        name='parameter_demo',
        output='screen',
        parameters=[config],
    )

    return LaunchDescription([parameter_demo])
