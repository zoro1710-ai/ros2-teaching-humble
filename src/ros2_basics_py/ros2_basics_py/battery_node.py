#!/usr/bin/env python3
"""Lesson 06 - calling a service from inside a node that keeps running.

Run both halves:
    ros2 run ros2_basics_py led_panel
    ros2 run ros2_basics_py battery_node

The battery drains for `discharge_time` seconds, then asks led_panel to switch
on LED 2, charges for `charge_time` seconds, then asks it to switch that LED
back off.

The important detail: this node has a timer, so it must never block. We use
call_async() plus add_done_callback() and return immediately. The response is
handled later, on the executor thread, when it actually arrives.
"""

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.srv import SetLed


class BatteryNode(Node):
    """Simulates a battery and drives one LED through the /set_led service."""

    def __init__(self):
        super().__init__('battery_node')

        self.declare_parameter('discharge_time', 4.0)
        self.declare_parameter('charge_time', 6.0)
        self.declare_parameter('led_number', 2)

        self._discharge_time = self.get_parameter('discharge_time').value
        self._charge_time = self.get_parameter('charge_time').value
        self._led_number = self.get_parameter('led_number').value

        self._is_empty = False
        self._client = self.create_client(SetLed, 'set_led')
        self._timer = self.create_timer(self._discharge_time, self.on_state_change)

        self.get_logger().info('battery_node started (full)')

    def on_state_change(self):
        self._is_empty = not self._is_empty

        if self._is_empty:
            self.get_logger().info('battery empty -> switching LED on')
        else:
            self.get_logger().info('battery full -> switching LED off')

        self.set_led(self._led_number, self._is_empty)

        # Re-arm the timer with the other duration.
        self._timer.cancel()
        period = self._charge_time if self._is_empty else self._discharge_time
        self._timer = self.create_timer(period, self.on_state_change)

    def set_led(self, led_number, state):
        if not self._client.service_is_ready():
            # Non-blocking check. Blocking here would stall the executor and
            # freeze every other callback in this node.
            self.get_logger().warn('/set_led not available yet, skipping')
            return

        request = SetLed.Request()
        request.led_number = led_number
        request.state = state

        future = self._client.call_async(request)
        future.add_done_callback(self.on_set_led_response)

    def on_set_led_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - we want to log any failure
            self.get_logger().error('service call failed: %r' % exc)
            return

        if not response.success:
            self.get_logger().warn('led_panel rejected the request')


def main(args=None):
    rclpy.init(args=args)
    node = BatteryNode()
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
