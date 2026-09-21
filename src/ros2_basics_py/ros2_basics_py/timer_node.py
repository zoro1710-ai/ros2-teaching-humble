#!/usr/bin/env python3
"""Lesson 03 - timers, the ROS 2 way to do periodic work.

Run it with:
    ros2 run ros2_basics_py timer_node

Never write `while True: ... time.sleep(1)` inside a node. That blocks the
executor and no other callback (subscriptions, services, parameters) can run.
Create a timer instead and let the executor call you back.
"""

import rclpy
from rclpy.node import Node


class TimerNode(Node):
    """Fires a callback twice per second and demonstrates the log levels."""

    def __init__(self):
        super().__init__('timer_node')
        self._tick = 0

        # create_timer(period_in_seconds, callback)
        self._timer = self.create_timer(0.5, self.on_timer)

        self.get_logger().info('timer_node started, ticking every 0.5 s')

    def on_timer(self):
        self._tick += 1

        # The five severity levels. Only INFO and above are printed by default;
        # show DEBUG with:  --ros-args --log-level timer_node:=debug
        self.get_logger().debug('debug: internal counter is %d' % self._tick)
        self.get_logger().info('tick %d' % self._tick)

        if self._tick % 10 == 0:
            self.get_logger().warn('ten ticks elapsed')

        # get_clock().now() is ROS time; it respects /clock when use_sim_time
        # is true, unlike time.time().
        if self._tick == 1:
            stamp = self.get_clock().now()
            self.get_logger().info('first tick at t=%.3f s' % (stamp.nanoseconds / 1e9))


def main(args=None):
    rclpy.init(args=args)
    node = TimerNode()
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
