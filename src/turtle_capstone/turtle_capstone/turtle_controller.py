#!/usr/bin/env python3
"""Capstone - drives turtle1 to catch every turtle that gets spawned.

This is the node that ties the whole course together:

    subscribes /turtle1/pose   (turtlesim/msg/Pose)   - where am I
    subscribes /alive_turtles  (TurtleArray)          - where are the targets
    publishes  /turtle1/cmd_vel (geometry_msgs/Twist) - how I move
    calls      /catch_turtle   (CatchTurtle)          - I got one

The control law is a proportional controller, the simplest useful feedback
controller there is:

    error    = target - current
    command  = gain * error

Two errors are used: the distance to the target drives linear speed, and the
angle between where the turtle is pointing and where the target is drives
angular speed. atan2 gives the target heading, and normalising the difference
into [-pi, pi] is what stops the turtle from spinning the long way round.
"""

import math

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.msg import TurtleArray
from ros2_basics_interfaces.srv import CatchTurtle
from turtlesim.msg import Pose


def normalize_angle(angle):
    """Wrap an angle in radians into the range [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class TurtleController(Node):
    """Chases the closest (or the oldest) living turtle."""

    def __init__(self):
        super().__init__('turtle_controller')

        self.declare_parameter('catch_closest_first', True)
        self.declare_parameter('linear_gain', 2.0)
        self.declare_parameter('angular_gain', 6.0)
        self.declare_parameter('catch_distance', 0.5)
        self.declare_parameter('control_period', 0.01)

        self._catch_closest_first = self.get_parameter('catch_closest_first').value
        self._linear_gain = self.get_parameter('linear_gain').value
        self._angular_gain = self.get_parameter('angular_gain').value
        self._catch_distance = self.get_parameter('catch_distance').value

        self._pose = None
        self._target = None

        self._cmd_publisher = self.create_publisher(Twist, 'turtle1/cmd_vel', 10)
        self._pose_subscriber = self.create_subscription(
            Pose, 'turtle1/pose', self.on_pose, 10)
        self._turtles_subscriber = self.create_subscription(
            TurtleArray, 'alive_turtles', self.on_alive_turtles, 10)
        self._catch_client = self.create_client(CatchTurtle, 'catch_turtle')

        period = self.get_parameter('control_period').value
        self._control_timer = self.create_timer(period, self.control_loop)

        self.get_logger().info('turtle_controller ready')

    # --- inputs ---
    def on_pose(self, msg):
        self._pose = msg

    def on_alive_turtles(self, msg):
        if not msg.turtles:
            self._target = None
            return

        if self._catch_closest_first and self._pose is not None:
            self._target = min(msg.turtles, key=self.distance_to)
        else:
            # Oldest first: the spawner appends, so index 0 is the oldest.
            self._target = msg.turtles[0]

    def distance_to(self, turtle):
        """Euclidean distance from our current pose to a turtle."""
        return math.hypot(turtle.x - self._pose.x, turtle.y - self._pose.y)

    # --- control ---
    def control_loop(self):
        if self._pose is None or self._target is None:
            # Nothing to chase: publish a zero command so the turtle coasts
            # to a stop instead of keeping its last velocity.
            self._cmd_publisher.publish(Twist())
            return

        distance = self.distance_to(self._target)
        cmd = Twist()

        if distance > self._catch_distance:
            # Proportional control on distance and on heading error.
            target_heading = math.atan2(
                self._target.y - self._pose.y, self._target.x - self._pose.x)
            heading_error = normalize_angle(target_heading - self._pose.theta)

            cmd.linear.x = self._linear_gain * distance
            cmd.angular.z = self._angular_gain * heading_error
        else:
            caught = self._target
            self._target = None
            self.call_catch_turtle(caught.name)

        self._cmd_publisher.publish(cmd)

    def call_catch_turtle(self, name):
        if not self._catch_client.service_is_ready():
            self.get_logger().warn('/catch_turtle is not available')
            return

        request = CatchTurtle.Request()
        request.name = name

        future = self._catch_client.call_async(request)
        future.add_done_callback(self.on_catch_response)

    def on_catch_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error('catch_turtle call failed: %r' % exc)
            return

        if not response.success:
            self.get_logger().warn('the spawner rejected the catch')


def main(args=None):
    rclpy.init(args=args)
    node = TurtleController()
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
