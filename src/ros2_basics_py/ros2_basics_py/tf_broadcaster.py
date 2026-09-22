#!/usr/bin/env python3
"""Lesson 12 - a dynamic transform.

Run it with:
    ros2 run ros2_basics_py tf_broadcaster
    ros2 run ros2_basics_py tf_listener

This node pretends a robot is driving in a circle and publishes the
odom -> base_link transform at 20 Hz on /tf.

Rules that save hours of debugging:
    * every transform needs a fresh header.stamp, or the listener will
      complain that the data is too old (extrapolation into the past),
    * a frame may have exactly ONE parent; two broadcasters publishing the
      same child frame is the classic "TF_REPEATED_DATA" warning,
    * rotations are quaternions, not Euler angles.
"""

import math

from geometry_msgs.msg import TransformStamped
import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def quaternion_from_yaw(yaw):
    """Convert a rotation about Z (in radians) into a quaternion tuple."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class TfBroadcaster(Node):
    """Publishes odom -> base_link for a robot driving in a circle."""

    def __init__(self):
        super().__init__('tf_broadcaster')

        self.declare_parameter('radius', 2.0)
        self.declare_parameter('angular_speed', 0.5)

        self._radius = self.get_parameter('radius').value
        self._angular_speed = self.get_parameter('angular_speed').value
        self._angle = 0.0

        self._broadcaster = TransformBroadcaster(self)
        self._timer = self.create_timer(0.05, self.publish_transform)

        self.get_logger().info('broadcasting odom -> base_link at 20 Hz')

    def publish_transform(self):
        self._angle += self._angular_speed * 0.05

        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_link'

        transform.transform.translation.x = self._radius * math.cos(self._angle)
        transform.transform.translation.y = self._radius * math.sin(self._angle)
        transform.transform.translation.z = 0.0

        # Face along the direction of travel.
        qx, qy, qz, qw = quaternion_from_yaw(self._angle + math.pi / 2.0)
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw

        self._broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = TfBroadcaster()
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
