#!/usr/bin/env python3
"""Lesson 10 - the subscriber half of the QoS demo.

See qos_publisher.py for the full explanation and the incompatible-QoS
experiment. Rule of thumb for compatibility:

    publisher RELIABLE        + subscriber BEST_EFFORT     -> connects
    publisher BEST_EFFORT     + subscriber RELIABLE        -> does NOT connect
    publisher TRANSIENT_LOCAL + subscriber VOLATILE        -> connects
    publisher VOLATILE        + subscriber TRANSIENT_LOCAL -> does NOT connect

The publisher must always offer at least as strong a guarantee as the
subscriber requests.
"""

import rclpy
from rclpy.node import Node
from ros2_basics_py.qos_publisher import PROFILES
from std_msgs.msg import String


class QosSubscriber(Node):
    """Subscribes to /qos_demo with a selectable QoS profile."""

    def __init__(self):
        super().__init__('qos_subscriber')

        self.declare_parameter('profile', 'default')
        name = self.get_parameter('profile').value

        if name not in PROFILES:
            raise ValueError(
                'unknown profile %r, expected one of %s' % (name, sorted(PROFILES)))

        self._subscription = self.create_subscription(
            String, 'qos_demo', self.on_message, PROFILES[name])

        self.get_logger().info('listening on /qos_demo with the "%s" profile' % name)
        self.get_logger().info(
            'if nothing arrives, run: ros2 topic info /qos_demo --verbose')

    def on_message(self, msg):
        self.get_logger().info('received %s' % msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = QosSubscriber()
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
