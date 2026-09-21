#!/usr/bin/env python3
"""Lesson 12 - looking a transform up.

Run the two broadcasters first, then:
    ros2 run ros2_basics_py tf_listener

A TransformListener fills a Buffer in the background. You then ask the buffer
questions like "where was the laser relative to odom at time T?" and TF2
interpolates between the samples it has.

The lookup can fail for perfectly normal reasons (the buffer is still filling
up, a broadcaster died, the timestamp is outside the buffer window), so a
lookup must ALWAYS be wrapped in try/except TransformException.

Passing rclpy.time.Time() - an all-zero timestamp - means "give me the most
recent transform available", which is what you want most of the time.
"""

import rclpy
from rclpy.node import Node
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener


class TfListener(Node):
    """Reports where the laser frame is, expressed in the odom frame."""

    def __init__(self):
        super().__init__('tf_listener')

        self.declare_parameter('target_frame', 'odom')
        self.declare_parameter('source_frame', 'laser')

        self._target = self.get_parameter('target_frame').value
        self._source = self.get_parameter('source_frame').value

        self._buffer = Buffer()
        self._listener = TransformListener(self._buffer, self)
        self._timer = self.create_timer(1.0, self.lookup)

        self.get_logger().info(
            'looking up %s -> %s once per second' % (self._target, self._source))

    def lookup(self):
        try:
            transform = self._buffer.lookup_transform(
                self._target, self._source, rclpy.time.Time())
        except TransformException as exc:
            self.get_logger().warn('lookup failed: %s' % exc)
            return

        t = transform.transform.translation
        self.get_logger().info(
            '%s is at x=%.2f y=%.2f z=%.2f in %s'
            % (self._source, t.x, t.y, t.z, self._target))


def main(args=None):
    rclpy.init(args=args)
    node = TfListener()
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
