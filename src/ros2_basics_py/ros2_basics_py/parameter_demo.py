#!/usr/bin/env python3
"""Lesson 07 - parameters done properly.

Run it with:
    ros2 run ros2_basics_py parameter_demo

Then from another terminal:
    ros2 param list
    ros2 param describe /parameter_demo robot_name
    ros2 param get /parameter_demo publish_frequency
    ros2 param set /parameter_demo publish_frequency 5.0      # accepted
    ros2 param set /parameter_demo publish_frequency 500.0    # rejected
    ros2 param dump /parameter_demo

Three things separate a toy parameter from a production one:
    1. a descriptor, so "ros2 param describe" explains it,
    2. a declared range, so obviously bad values are refused by the middleware,
    3. a set-callback, so the node reacts to changes instead of needing a restart.
"""

from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
import rclpy
from rclpy.node import Node


class ParameterDemo(Node):
    """A node whose behaviour can be retuned at runtime."""

    def __init__(self):
        super().__init__('parameter_demo')

        self.declare_parameter(
            'robot_name',
            'rosbot',
            ParameterDescriptor(description='Name used in the log lines.'))

        self.declare_parameter(
            'publish_frequency',
            1.0,
            ParameterDescriptor(
                description='How often the node logs, in Hz.',
                floating_point_range=[
                    FloatingPointRange(from_value=0.1, to_value=10.0, step=0.0)
                ]))

        self.declare_parameter(
            'enabled',
            True,
            ParameterDescriptor(description='Set false to mute the node.'))

        self._robot_name = self.get_parameter('robot_name').value
        self._enabled = self.get_parameter('enabled').value
        frequency = self.get_parameter('publish_frequency').value

        self._timer = self.create_timer(1.0 / frequency, self.on_timer)

        # Runs before a new value is committed. Return success=False to veto.
        self.add_on_set_parameters_callback(self.on_parameter_change)

        self.get_logger().info('parameter_demo started as "%s"' % self._robot_name)

    def on_timer(self):
        if self._enabled:
            self.get_logger().info('%s is alive' % self._robot_name)

    def on_parameter_change(self, params):
        for param in params:
            if param.name == 'robot_name':
                if not param.value:
                    return SetParametersResult(
                        successful=False, reason='robot_name must not be empty')
                self._robot_name = param.value

            elif param.name == 'enabled':
                self._enabled = param.value

            elif param.name == 'publish_frequency':
                # The declared range already blocks values outside 0.1 - 10.0,
                # so here we only need to re-arm the timer.
                self._timer.cancel()
                self._timer = self.create_timer(1.0 / param.value, self.on_timer)
                self.get_logger().info('frequency is now %.2f Hz' % param.value)

        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = ParameterDemo()
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
