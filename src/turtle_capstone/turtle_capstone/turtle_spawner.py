#!/usr/bin/env python3
"""Capstone - spawns turtles and removes the ones that get caught.

This node is a pure "service orchestration" node: it owns no hardware and does
almost no maths. What it does is call other nodes' services and keep a list of
what is currently alive.

    calls     /spawn          (turtlesim)  to create a turtle
    calls     /kill           (turtlesim)  to remove a caught one
    publishes /alive_turtles  (TurtleArray)
    serves    /catch_turtle   (CatchTurtle)

Every service call uses call_async plus a done-callback. functools.partial is
how we smuggle the extra context (the turtle we just asked for) into that
callback, since the callback itself only receives the future.
"""

from functools import partial
import math
import random

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.msg import Turtle, TurtleArray
from ros2_basics_interfaces.srv import CatchTurtle
from turtlesim.srv import Kill, Spawn


class TurtleSpawner(Node):
    """Keeps a population of turtles alive in the turtlesim window."""

    def __init__(self):
        super().__init__('turtle_spawner')

        self.declare_parameter('spawn_frequency', 0.5)
        self.declare_parameter('turtle_name_prefix', 'turtle')

        self._spawn_frequency = self.get_parameter('spawn_frequency').value
        self._prefix = self.get_parameter('turtle_name_prefix').value

        # turtlesim always starts with turtle1, so our first one is turtle2.
        self._counter = 1
        self._alive_turtles = []

        self._publisher = self.create_publisher(TurtleArray, 'alive_turtles', 10)
        self._spawn_client = self.create_client(Spawn, 'spawn')
        self._kill_client = self.create_client(Kill, 'kill')
        self._catch_service = self.create_service(
            CatchTurtle, 'catch_turtle', self.on_catch_request)

        self._timer = self.create_timer(1.0 / self._spawn_frequency, self.spawn_turtle)

        self.get_logger().info('turtle_spawner ready')

    # --- publishing ---
    def publish_alive_turtles(self):
        msg = TurtleArray()
        msg.turtles = self._alive_turtles
        self._publisher.publish(msg)

    # --- spawning ---
    def spawn_turtle(self):
        if not self._spawn_client.service_is_ready():
            self.get_logger().info('waiting for the /spawn service ...')
            return

        self._counter += 1
        name = '%s%d' % (self._prefix, self._counter)

        request = Spawn.Request()
        request.x = random.uniform(1.0, 10.0)
        request.y = random.uniform(1.0, 10.0)
        request.theta = random.uniform(0.0, 2.0 * math.pi)
        request.name = name

        future = self._spawn_client.call_async(request)
        # partial() binds the turtle we asked for to the callback, because the
        # callback signature only gives us the future.
        future.add_done_callback(
            partial(self.on_spawn_response, name=name, x=request.x, y=request.y,
                    theta=request.theta))

    def on_spawn_response(self, future, name, x, y, theta):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error('spawn call failed: %r' % exc)
            return

        if not response.name:
            self.get_logger().warn('turtlesim refused to spawn %s' % name)
            return

        turtle = Turtle()
        turtle.name = response.name
        turtle.x = x
        turtle.y = y
        turtle.theta = theta

        self._alive_turtles.append(turtle)
        self.publish_alive_turtles()
        self.get_logger().info('spawned %s at (%.2f, %.2f)' % (response.name, x, y))

    # --- catching ---
    def on_catch_request(self, request, response):
        if not any(turtle.name == request.name for turtle in self._alive_turtles):
            self.get_logger().warn('%s is not alive' % request.name)
            response.success = False
            return response

        self.call_kill(request.name)
        response.success = True
        return response

    def call_kill(self, name):
        if not self._kill_client.service_is_ready():
            self.get_logger().warn('/kill is not available')
            return

        request = Kill.Request()
        request.name = name

        future = self._kill_client.call_async(request)
        future.add_done_callback(partial(self.on_kill_response, name=name))

    def on_kill_response(self, future, name):
        try:
            future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error('kill call failed: %r' % exc)
            return

        self._alive_turtles = [t for t in self._alive_turtles if t.name != name]
        self.publish_alive_turtles()
        self.get_logger().info('caught %s (%d left)' % (name, len(self._alive_turtles)))


def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawner()
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
