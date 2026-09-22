#!/usr/bin/env python3
"""Lesson 06 - publishing a custom message.

Run it with:
    ros2 run ros2_basics_py hardware_status_publisher

Inspect the interface you built:
    ros2 interface show ros2_basics_interfaces/msg/HardwareStatus
    ros2 topic echo /hardware_status
"""

import random

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.msg import HardwareStatus


class HardwareStatusPublisher(Node):
    """Publishes a fake hardware status once per second."""

    def __init__(self):
        super().__init__('hardware_status_publisher')

        self._publisher = self.create_publisher(HardwareStatus, 'hardware_status', 10)
        self._timer = self.create_timer(1.0, self.publish_status)

        self.get_logger().info('publishing on /hardware_status')

    def publish_status(self):
        msg = HardwareStatus()
        msg.temperature = round(random.uniform(35.0, 70.0), 2)
        msg.are_motors_ready = msg.temperature < 65.0
        msg.debug_message = (
            'nominal' if msg.are_motors_ready else 'overheating, motors disabled')
        self._publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = HardwareStatusPublisher()
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
