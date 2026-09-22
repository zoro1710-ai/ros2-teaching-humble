#!/usr/bin/env python3
"""Lesson 04/05 - a node that subscribes, publishes and serves a request.

Run it together with the publisher:
    ros2 run ros2_basics_py number_publisher
    ros2 run ros2_basics_py number_counter

Watch the running total:
    ros2 topic echo /number_count

Reset it from the command line:
    ros2 service call /reset_counter std_srvs/srv/SetBool "{data: true}"

This is the shape of most real ROS 2 nodes: some inputs (a subscription),
some outputs (a publisher) and a way for the rest of the system to change
its state (a service).
"""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool


class NumberCounter(Node):
    """Accumulates everything published on /number."""

    def __init__(self):
        super().__init__('number_counter')

        self._counter = 0

        self._publisher = self.create_publisher(Int64, 'number_count', 10)
        self._subscription = self.create_subscription(
            Int64, 'number', self.on_number, 10)
        self._reset_service = self.create_service(
            SetBool, 'reset_counter', self.on_reset_request)

        self.get_logger().info('number_counter ready')

    # --- pure logic, kept separate so it can be unit tested without ROS ---
    def accumulate(self, value):
        """Add `value` to the running total and return the new total."""
        self._counter += value
        return self._counter

    def reset(self):
        """Set the running total back to zero."""
        self._counter = 0

    @property
    def counter(self):
        return self._counter

    # --- ROS callbacks ---
    def on_number(self, msg):
        total = self.accumulate(msg.data)
        out = Int64()
        out.data = total
        self._publisher.publish(out)

    def on_reset_request(self, request, response):
        # A service callback must fill in `response` and return it.
        # It runs on the executor thread, so keep it fast and never block.
        if request.data:
            previous = self._counter
            self.reset()
            response.success = True
            response.message = 'counter reset (was %d)' % previous
        else:
            response.success = False
            response.message = 'set data:=true to actually reset'

        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = NumberCounter()
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
