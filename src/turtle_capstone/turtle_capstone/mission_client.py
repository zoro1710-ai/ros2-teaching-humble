#!/usr/bin/env python3
"""Grand finale - the button you press to start (and cancel) the show.

Usage:
    ros2 run turtle_capstone mission_client            # catch 5 turtles
    ros2 run turtle_capstone mission_client 10         # catch 10

It sends one CatchMission goal, prints the feedback as it streams in, and prints
the result at the end. Press Ctrl-C while it is running to CANCEL the mission -
the turtle stops where it is and the server reports how many it managed. That is
the whole point of an action: a long job you can watch and abort, unlike a
service (fire once, one answer) or a topic (a stream with no request).
"""

import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from ros2_basics_interfaces.action import CatchMission


class MissionClient(Node):
    """Sends a catch_mission goal and reports progress."""

    def __init__(self, turtle_count):
        super().__init__('mission_client')
        self._turtle_count = turtle_count
        self._client = ActionClient(self, CatchMission, 'catch_mission')
        self._goal_handle = None
        # Set once the mission ends (result received or goal rejected). main()
        # watches this instead of shutting rclpy down from inside a callback,
        # which would invalidate the context the spin loop is still using.
        self.finished = False

    def send_goal(self):
        self.get_logger().info('waiting for the mission_control action server ...')
        self._client.wait_for_server()

        goal = CatchMission.Goal()
        goal.turtle_count = self._turtle_count
        self.get_logger().info('sending goal: catch %d turtles' % self._turtle_count)

        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._on_feedback)
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().error('goal rejected')
            self.finished = True
            return
        self.get_logger().info('goal accepted - the hunt is on')
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(
            'caught %d | remaining %d | chasing %s (%.2f m away)' % (
                fb.caught_so_far, fb.remaining, fb.current_target,
                fb.distance_to_target))

    def _on_result(self, future):
        result = future.result().result
        self.get_logger().info(
            'MISSION OVER: %d caught in %.1f s' % (
                result.total_caught, result.elapsed_seconds))
        self.finished = True

    def cancel(self):
        if self._goal_handle is not None:
            self.get_logger().info('Ctrl-C: canceling the mission ...')
            self._goal_handle.cancel_goal_async()


def main(args=None):
    rclpy.init(args=args)

    turtle_count = 5
    argv = args if args is not None else sys.argv[1:]
    if argv:
        try:
            turtle_count = int(argv[0])
        except ValueError:
            pass

    node = MissionClient(turtle_count)
    node.send_goal()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        # Ask the server to cancel, then keep spinning briefly so the cancel
        # request is delivered and the (canceled) result comes back.
        node.cancel()
        deadline = time.time() + 3.0
        while rclpy.ok() and not node.finished and time.time() < deadline:
            try:
                rclpy.spin_once(node, timeout_sec=0.1)
            except KeyboardInterrupt:
                break
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
