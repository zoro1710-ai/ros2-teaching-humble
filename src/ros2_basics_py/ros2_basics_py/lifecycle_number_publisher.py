#!/usr/bin/env python3
"""Lesson 13 - managed (lifecycle) nodes.

Run it with:
    ros2 run ros2_basics_py lifecycle_number_publisher

Drive the state machine from another terminal:
    ros2 lifecycle nodes
    ros2 lifecycle get  /lifecycle_number_publisher
    ros2 lifecycle set  /lifecycle_number_publisher configure
    ros2 lifecycle set  /lifecycle_number_publisher activate
    ros2 topic echo /lifecycle_number
    ros2 lifecycle set  /lifecycle_number_publisher deactivate
    ros2 lifecycle set  /lifecycle_number_publisher cleanup

A plain node starts doing its job the moment it launches. A lifecycle node
waits to be told. The four primary states are:

    unconfigured -> (configure)  -> inactive
    inactive     -> (activate)   -> active
    active       -> (deactivate) -> inactive
    inactive     -> (cleanup)    -> unconfigured

Why it matters: a driver can allocate its hardware in on_configure, and the
system integrator decides exactly when it starts publishing. A lifecycle
publisher created in on_configure silently drops messages while inactive, so
nothing leaks out before the node is meant to be running.
"""

from example_interfaces.msg import Int64
import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn


class LifecycleNumberPublisher(Node):
    """Publishes an incrementing number, but only while it is active."""

    def __init__(self):
        super().__init__('lifecycle_number_publisher')
        self._publisher = None
        self._timer = None
        self._counter = 0
        self.get_logger().info('constructed, currently unconfigured')

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Allocate resources. Still not publishing anything."""
        self.get_logger().info('on_configure: creating publisher and timer')
        self._publisher = self.create_lifecycle_publisher(Int64, 'lifecycle_number', 10)
        self._timer = self.create_timer(1.0, self.publish_number)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start doing the real work."""
        self.get_logger().info('on_activate: now publishing')
        # The base class flips the publisher into its active state.
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop publishing but keep everything allocated."""
        self.get_logger().info('on_deactivate: pausing')
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Release everything acquired in on_configure."""
        self.get_logger().info('on_cleanup: destroying publisher and timer')
        self.destroy_timer(self._timer)
        self.destroy_lifecycle_publisher(self._publisher)
        self._timer = None
        self._publisher = None
        self._counter = 0
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('on_shutdown')
        return TransitionCallbackReturn.SUCCESS

    def publish_number(self):
        self._counter += 1
        msg = Int64()
        msg.data = self._counter
        # While the node is inactive this publish is a no-op.
        self._publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LifecycleNumberPublisher()
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
