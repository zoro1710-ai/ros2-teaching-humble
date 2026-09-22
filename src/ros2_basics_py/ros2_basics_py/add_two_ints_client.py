#!/usr/bin/env python3
"""Lesson 05 - a one-shot service client.

Run the server first, then:
    ros2 run ros2_basics_py add_two_ints_client 3 4

This is the "script" style of client: send one request, wait for the answer,
exit. It is safe here because the node is not spinning for anything else.
Inside a node that also has timers or subscriptions, never block like this -
use the callback style shown in rectangle_area_client.py instead.
"""

import sys

from example_interfaces.srv import AddTwoInts
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args


class AddTwoIntsClient(Node):
    """Sends a single AddTwoInts request and reports the result."""

    def __init__(self):
        super().__init__('add_two_ints_client')
        self._client = self.create_client(AddTwoInts, 'add_two_ints')

    def send_request(self, a, b):
        # A client that calls a service nobody provides would hang forever,
        # so always wait (with a timeout) for the server to appear.
        while not self._client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /add_two_ints ...')

        request = AddTwoInts.Request()
        request.a = a
        request.b = b

        future = self._client.call_async(request)
        # Spin this node until the future is resolved. Do NOT use the
        # blocking client.call() inside a callback: it deadlocks.
        rclpy.spin_until_future_complete(self, future)
        return future.result()


def main(args=None):
    rclpy.init(args=args)

    # Strip the --ros-args block so we can read our own positional arguments.
    argv = remove_ros_args(sys.argv)
    a = int(argv[1]) if len(argv) > 1 else 3
    b = int(argv[2]) if len(argv) > 2 else 4

    node = AddTwoIntsClient()
    try:
        response = node.send_request(a, b)
        node.get_logger().info('%d + %d = %d' % (a, b, response.sum))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
