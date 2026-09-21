#!/usr/bin/env python3
"""Lesson 05 - a service server using a ready-made interface.

Run it with:
    ros2 run ros2_basics_py add_two_ints_server

Call it without writing any client code:
    ros2 service list
    ros2 service type /add_two_ints
    ros2 interface show example_interfaces/srv/AddTwoInts
    ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 3, b: 4}"
"""

from example_interfaces.srv import AddTwoInts
import rclpy
from rclpy.node import Node


class AddTwoIntsServer(Node):
    """Answers /add_two_ints with the sum of the two requested integers."""

    def __init__(self):
        super().__init__('add_two_ints_server')

        # create_service(srv_type, service_name, callback)
        self._service = self.create_service(
            AddTwoInts, 'add_two_ints', self.on_request)

        self.get_logger().info('add_two_ints server ready')

    def on_request(self, request, response):
        response.sum = request.a + request.b
        self.get_logger().info(
            '%d + %d = %d' % (request.a, request.b, response.sum))
        return response


def main(args=None):
    rclpy.init(args=args)
    node = AddTwoIntsServer()
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
