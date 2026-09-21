#!/usr/bin/env python3
"""Lesson 04 - the classic subscriber.

Run it with:
    ros2 run ros2_basics_py listener

A subscriber has no loop of its own. You register a callback and the executor
calls it once per incoming message. Keep callbacks short: while one runs, a
single-threaded executor cannot run anything else.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    """Prints every message received on /chatter."""

    def __init__(self):
        super().__init__('listener')

        # create_subscription(msg_type, topic_name, callback, qos)
        # The topic name, type and QoS must all match the publisher or the
        # two will never connect. `ros2 topic info /chatter --verbose` shows why.
        self._subscription = self.create_subscription(
            String, 'chatter', self.on_message, 10)

        self.get_logger().info('listener waiting for messages on /chatter')

    def on_message(self, msg):
        self.get_logger().info('heard "%s"' % msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
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
