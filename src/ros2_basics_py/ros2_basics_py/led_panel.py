#!/usr/bin/env python3
"""Lesson 06 - a service server that uses a *custom* interface.

Run it with:
    ros2 run ros2_basics_py led_panel

Drive it by hand:
    ros2 service call /set_led ros2_basics_interfaces/srv/SetLed "{led_number: 2, state: true}"
    ros2 topic echo /led_states

Or let battery_node drive it automatically (lesson 06).
"""

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.srv import SetLed
from std_msgs.msg import String


class LedPanel(Node):
    """Owns the state of a three LED panel and publishes it."""

    def __init__(self):
        super().__init__('led_panel')

        self.declare_parameter('led_count', 3)
        led_count = self.get_parameter('led_count').value

        self._leds = [False] * led_count

        self._publisher = self.create_publisher(String, 'led_states', 10)
        self._service = self.create_service(SetLed, 'set_led', self.on_set_led)
        self._timer = self.create_timer(1.0, self.publish_states)

        self.get_logger().info('led_panel ready with %d LEDs' % led_count)

    def publish_states(self):
        msg = String()
        msg.data = ' '.join('ON' if led else 'off' for led in self._leds)
        self._publisher.publish(msg)

    def on_set_led(self, request, response):
        # Validate the request. A service that returns success=False with a
        # clear reason is far easier to debug than one that throws.
        if not 0 <= request.led_number < len(self._leds):
            response.success = False
            self.get_logger().warn(
                'rejected: led_number %d is out of range' % request.led_number)
            return response

        self._leds[request.led_number] = request.state
        response.success = True
        self.get_logger().info(
            'LED %d -> %s' % (request.led_number, 'ON' if request.state else 'off'))
        self.publish_states()
        return response


def main(args=None):
    rclpy.init(args=args)
    node = LedPanel()
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
