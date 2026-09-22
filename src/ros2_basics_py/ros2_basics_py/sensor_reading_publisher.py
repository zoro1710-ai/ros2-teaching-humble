#!/usr/bin/env python3
"""Lesson 06 - a custom message that embeds std_msgs/Header.

Run it with:
    ros2 run ros2_basics_py sensor_reading_publisher

Almost every real sensor message carries a Header, which gives you:
    header.stamp     - when the data was measured (ROS time, not wall time)
    header.frame_id  - which coordinate frame it belongs to

Those two fields are what let TF2 and message_filters line data up correctly.
"""

import math

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.msg import SensorReading


class SensorReadingPublisher(Node):
    """Publishes a smooth synthetic sensor signal at 10 Hz."""

    def __init__(self):
        super().__init__('sensor_reading_publisher')

        self.declare_parameter('sensor_id', 'imu_0')
        self.declare_parameter('frame_id', 'base_link')

        self._sensor_id = self.get_parameter('sensor_id').value
        self._frame_id = self.get_parameter('frame_id').value
        self._t = 0.0

        self._publisher = self.create_publisher(SensorReading, 'sensor_reading', 10)
        self._timer = self.create_timer(0.1, self.publish_reading)

        self.get_logger().info(
            'publishing %s on /sensor_reading in frame %s'
            % (self._sensor_id, self._frame_id))

    def publish_reading(self):
        self._t += 0.1

        msg = SensorReading()
        # to_msg() converts the rclpy Time object into builtin_interfaces/Time.
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.sensor_id = self._sensor_id
        msg.value = 9.81 + 0.5 * math.sin(self._t)
        msg.unit = 'm/s^2'

        self._publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorReadingPublisher()
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
