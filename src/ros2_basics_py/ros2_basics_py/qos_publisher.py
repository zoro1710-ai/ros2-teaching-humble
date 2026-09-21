#!/usr/bin/env python3
"""Lesson 10 - QoS profiles, and why topics sometimes silently do nothing.

Run it with:
    ros2 run ros2_basics_py qos_publisher --ros-args -p profile:=sensor
    ros2 run ros2_basics_py qos_subscriber --ros-args -p profile:=sensor    # works
    ros2 run ros2_basics_py qos_subscriber --ros-args -p profile:=default   # NO data

The second combination is the single most common "my topic is dead" bug:
a BEST_EFFORT publisher and a RELIABLE subscriber are incompatible, so the
middleware never connects them. "ros2 topic info /qos_demo --verbose" and the
QoS warning in the log are how you spot it.

Profiles available here:
    default  - reliable, volatile, keep last 10
    sensor   - best effort, volatile, keep last 5 (for high-rate sensor data)
    latched  - reliable, transient local, keep last 1 (late joiners get the
               last value immediately; this is how /robot_description works)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

PROFILES = {
    'default': QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10),
    'sensor': QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=5),
    'latched': QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1),
}


class QosPublisher(Node):
    """Publishes on /qos_demo with a selectable QoS profile."""

    def __init__(self):
        super().__init__('qos_publisher')

        self.declare_parameter('profile', 'default')
        name = self.get_parameter('profile').value

        if name not in PROFILES:
            raise ValueError(
                'unknown profile %r, expected one of %s' % (name, sorted(PROFILES)))

        self._publisher = self.create_publisher(String, 'qos_demo', PROFILES[name])
        self._count = 0
        self._timer = self.create_timer(0.5, self.publish_message)

        self.get_logger().info('publishing /qos_demo with the "%s" profile' % name)

    def publish_message(self):
        msg = String()
        msg.data = 'sample %d' % self._count
        self._publisher.publish(msg)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = QosPublisher()
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
