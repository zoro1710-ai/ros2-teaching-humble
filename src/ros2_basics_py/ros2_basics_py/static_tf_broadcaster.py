#!/usr/bin/env python3
"""Lesson 12 - a static transform.

Run it with:
    ros2 run ros2_basics_py static_tf_broadcaster

    ros2 run tf2_tools view_frames          # writes frames.pdf
    ros2 run tf2_ros tf2_echo base_link laser

A static transform is one that never changes: a sensor bolted to the chassis,
the offset between base_link and base_footprint. Publish it ONCE on /tf_static
with a StaticTransformBroadcaster - it uses TRANSIENT_LOCAL durability, so any
node that starts later still receives it.

Never publish a static transform on a timer. That is what the (non-static)
TransformBroadcaster is for.
"""

from geometry_msgs.msg import TransformStamped
import rclpy
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster


class StaticTfBroadcaster(Node):
    """Publishes a fixed base_link -> laser transform."""

    def __init__(self):
        super().__init__('static_tf_broadcaster')

        self.declare_parameter('parent_frame', 'base_link')
        self.declare_parameter('child_frame', 'laser')
        self.declare_parameter('translation', [0.2, 0.0, 0.15])

        self._broadcaster = StaticTransformBroadcaster(self)
        self.publish_transform()

    def publish_transform(self):
        parent = self.get_parameter('parent_frame').value
        child = self.get_parameter('child_frame').value
        xyz = self.get_parameter('translation').value

        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = parent
        transform.child_frame_id = child

        transform.transform.translation.x = float(xyz[0])
        transform.transform.translation.y = float(xyz[1])
        transform.transform.translation.z = float(xyz[2])

        # Identity rotation as a quaternion (x, y, z, w).
        # w = 1.0 with the rest zero means "no rotation". A quaternion of all
        # zeros is invalid and TF2 will reject it.
        transform.transform.rotation.x = 0.0
        transform.transform.rotation.y = 0.0
        transform.transform.rotation.z = 0.0
        transform.transform.rotation.w = 1.0

        self._broadcaster.sendTransform(transform)
        self.get_logger().info(
            'published static transform %s -> %s' % (parent, child))


def main(args=None):
    rclpy.init(args=args)
    node = StaticTfBroadcaster()
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
