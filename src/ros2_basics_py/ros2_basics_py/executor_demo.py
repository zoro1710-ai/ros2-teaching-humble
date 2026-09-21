#!/usr/bin/env python3
"""Lesson 11 - executors and callback groups.

Run it with:
    ros2 run ros2_basics_py executor_demo                                  # single threaded
    ros2 run ros2_basics_py executor_demo --ros-args -p multi_threaded:=true

This node has two timers. The "slow" one deliberately blocks for 2 seconds.

    single threaded  -> the fast timer stops ticking while the slow one runs
    multi threaded + ReentrantCallbackGroup -> both keep ticking

This is the mental model to keep: rclpy.spin() is a loop that pulls ready
callbacks off a queue and runs them. One thread means one callback at a time.
Callback groups decide which callbacks are allowed to overlap:

    MutuallyExclusiveCallbackGroup (the default) - never overlap each other
    ReentrantCallbackGroup                       - may overlap freely

Blocking inside a callback is the number one cause of "my node froze".
"""

import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node


class ExecutorDemo(Node):
    """Two timers, one of which blocks, to make executor behaviour visible."""

    def __init__(self):
        super().__init__('executor_demo')

        self.declare_parameter('multi_threaded', False)
        self._multi_threaded = self.get_parameter('multi_threaded').value

        if self._multi_threaded:
            group = ReentrantCallbackGroup()
        else:
            group = MutuallyExclusiveCallbackGroup()

        self._fast_timer = self.create_timer(0.25, self.fast_tick, callback_group=group)
        self._slow_timer = self.create_timer(3.0, self.slow_tick, callback_group=group)
        self._fast_ticks = 0

        self.get_logger().info(
            'executor_demo running %s'
            % ('multi threaded' if self._multi_threaded else 'single threaded'))

    def fast_tick(self):
        self._fast_ticks += 1
        self.get_logger().info('fast tick %d' % self._fast_ticks)

    def slow_tick(self):
        self.get_logger().warn('slow callback START (blocking for 2 s)')
        time.sleep(2.0)
        self.get_logger().warn('slow callback END')


def main(args=None):
    rclpy.init(args=args)
    node = ExecutorDemo()

    if node.get_parameter('multi_threaded').value:
        executor = MultiThreadedExecutor(num_threads=4)
    else:
        executor = SingleThreadedExecutor()

    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
