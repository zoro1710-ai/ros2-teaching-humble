#!/usr/bin/env python3
"""Lesson 06 - a service server built on a custom .srv file.

Run it with:
    ros2 run ros2_basics_py rectangle_area_server

    ros2 interface show ros2_basics_interfaces/srv/ComputeRectangleArea
    ros2 service call /compute_rectangle_area \
        ros2_basics_interfaces/srv/ComputeRectangleArea "{length: 3.0, width: 4.0}"
"""

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.srv import ComputeRectangleArea


class RectangleAreaServer(Node):
    """Computes length * width, rejecting negative input."""

    def __init__(self):
        super().__init__('rectangle_area_server')

        self._service = self.create_service(
            ComputeRectangleArea, 'compute_rectangle_area', self.on_request)

        self.get_logger().info('compute_rectangle_area server ready')

    def on_request(self, request, response):
        if request.length < 0.0 or request.width < 0.0:
            response.area = 0.0
            response.message = 'length and width must be >= 0'
            self.get_logger().warn(response.message)
            return response

        response.area = request.length * request.width
        response.message = 'ok'
        self.get_logger().info(
            '%.2f x %.2f = %.2f' % (request.length, request.width, response.area))
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RectangleAreaServer()
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
