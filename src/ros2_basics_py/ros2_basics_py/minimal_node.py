#!/usr/bin/env python3
"""Lesson 03 - the smallest useful ROS 2 node.

Run it with:
    ros2 run ros2_basics_py minimal_node

Every rclpy program has the same four steps:
    1. rclpy.init()      -> talk to the ROS 2 middleware
    2. create a Node     -> your unit of computation
    3. rclpy.spin(node)  -> hand control to ROS so callbacks can fire
    4. rclpy.shutdown()  -> clean up

This node has no publishers, subscribers or timers, so spin() just blocks
until you press Ctrl+C. That is fine: it still shows up in `ros2 node list`.
"""

import rclpy
from rclpy.node import Node


class MinimalNode(Node):
    """A node that only logs once and then idles."""

    def __init__(self):
        # 'minimal_node' is the *default* node name. It can be overridden at
        # runtime with:  ros2 run ros2_basics_py minimal_node --ros-args -r __node:=other
        super().__init__('minimal_node')
        self.get_logger().info('Hello from %s' % self.get_name())


def main(args=None):
    rclpy.init(args=args)
    node = MinimalNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
