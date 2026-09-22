#!/usr/bin/env python3
"""Lesson 04/07 - a publisher whose behaviour is driven by parameters.

Run it with defaults:
    ros2 run ros2_basics_py number_publisher

Or override the parameters on the command line:
    ros2 run ros2_basics_py number_publisher --ros-args -p number:=7 -p publish_frequency:=5.0

This node is the first half of the number_publisher / number_counter pair used
throughout the course.
"""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node


class NumberPublisher(Node):
    """Publishes a fixed number on /number at a configurable frequency."""

    def __init__(self):
        super().__init__('number_publisher')

        # Declare before you get. An undeclared parameter raises
        # ParameterNotDeclaredException, which is the behaviour you want:
        # typos fail loudly instead of silently returning a default.
        self.declare_parameter('number', 2)
        self.declare_parameter('publish_frequency', 1.0)

        self._number = self.get_parameter('number').value
        frequency = self.get_parameter('publish_frequency').value

        self._publisher = self.create_publisher(Int64, 'number', 10)
        self._timer = self.create_timer(1.0 / frequency, self.publish_number)

        self.get_logger().info(
            'publishing %d on /number at %.1f Hz' % (self._number, frequency))

    def publish_number(self):
        msg = Int64()
        msg.data = self._number
        self._publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = NumberPublisher()
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
