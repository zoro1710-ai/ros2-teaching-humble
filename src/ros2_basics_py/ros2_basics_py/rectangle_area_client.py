#!/usr/bin/env python3
"""Lesson 06 - the non-blocking client pattern.

Run the server first, then:
    ros2 run ros2_basics_py rectangle_area_client

Unlike add_two_ints_client.py, this node keeps running: a timer fires a new
request every two seconds and a done-callback picks the answer up later.
That is the pattern you want inside any node that does more than one thing.
"""

import random

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.srv import ComputeRectangleArea


class RectangleAreaClient(Node):
    """Periodically asks the server for the area of a random rectangle."""

    def __init__(self):
        super().__init__('rectangle_area_client')

        self._client = self.create_client(
            ComputeRectangleArea, 'compute_rectangle_area')
        self._timer = self.create_timer(2.0, self.request_area)

        self.get_logger().info('rectangle_area_client started')

    def request_area(self):
        if not self._client.service_is_ready():
            self.get_logger().info('waiting for /compute_rectangle_area ...')
            return

        request = ComputeRectangleArea.Request()
        request.length = round(random.uniform(1.0, 10.0), 2)
        request.width = round(random.uniform(1.0, 10.0), 2)

        self.get_logger().info(
            'requesting area of %.2f x %.2f' % (request.length, request.width))

        future = self._client.call_async(request)
        future.add_done_callback(self.on_response)

    def on_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - log whatever went wrong
            self.get_logger().error('call failed: %r' % exc)
            return

        self.get_logger().info(
            'area = %.2f (%s)' % (response.area, response.message))


def main(args=None):
    rclpy.init(args=args)
    node = RectangleAreaClient()
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
