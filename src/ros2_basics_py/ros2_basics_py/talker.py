#!/usr/bin/env python3
"""Lesson 04 - the classic publisher.

Run it with:
    ros2 run ros2_basics_py talker

Then inspect it from another terminal:
    ros2 topic list
    ros2 topic echo /chatter
    ros2 topic hz /chatter
    ros2 topic info /chatter --verbose
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    """Publishes an incrementing greeting on /chatter."""

    def __init__(self):
        super().__init__('talker')

        # create_publisher(msg_type, topic_name, qos)
        # The plain integer 10 is shorthand for "keep last 10, reliable".
        self._publisher = self.create_publisher(String, 'chatter', 10)
        self._count = 0
        self._timer = self.create_timer(0.5, self.publish_message)

        self.get_logger().info('talker publishing on /chatter')

    def publish_message(self):
        msg = String()
        msg.data = 'Hello ROS 2: %d' % self._count
        self._publisher.publish(msg)
        self.get_logger().info('published "%s"' % msg.data)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
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
