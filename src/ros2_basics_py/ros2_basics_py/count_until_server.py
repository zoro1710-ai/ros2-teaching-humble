#!/usr/bin/env python3
"""Lesson 09 - an action server.

Run it with:
    ros2 run ros2_basics_py count_until_server

Send a goal from the command line and watch the feedback stream:
    ros2 action list
    ros2 action info /count_until -t
    ros2 action send_goal /count_until ros2_basics_interfaces/action/CountUntil \
        "{target_number: 5, period: 1.0}" --feedback

Use an action (not a service) when the work takes a long time, when the caller
wants progress updates, or when the caller must be able to cancel. An action is
built from three services (send_goal, cancel_goal, get_result) plus two topics
(feedback, status) - the ActionServer class hides all of that.

Threading note: execute_callback blocks while it counts. With the default
single-threaded executor, a cancel request arriving during that time could
never be processed. That is why this node uses a ReentrantCallbackGroup and a
MultiThreadedExecutor.
"""

import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from ros2_basics_interfaces.action import CountUntil


class CountUntilServer(Node):
    """Counts up to the requested number, one step per period."""

    def __init__(self):
        super().__init__('count_until_server')

        self._action_server = ActionServer(
            self,
            CountUntil,
            'count_until',
            goal_callback=self.on_goal_request,
            cancel_callback=self.on_cancel_request,
            execute_callback=self.execute,
            callback_group=ReentrantCallbackGroup())

        self.get_logger().info('count_until action server ready')

    def on_goal_request(self, goal_request):
        """Decide whether to accept a new goal. Runs before execute()."""
        if goal_request.target_number <= 0:
            self.get_logger().warn('rejecting goal: target_number must be > 0')
            return GoalResponse.REJECT

        if goal_request.period <= 0.0:
            self.get_logger().warn('rejecting goal: period must be > 0')
            return GoalResponse.REJECT

        self.get_logger().info(
            'accepted goal: count to %d every %.2f s'
            % (goal_request.target_number, goal_request.period))
        return GoalResponse.ACCEPT

    def on_cancel_request(self, goal_handle):
        """Decide whether a cancel request is allowed. Almost always ACCEPT."""
        self.get_logger().info('cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        """Do the actual work and return a Result."""
        target = goal_handle.request.target_number
        period = goal_handle.request.period

        feedback = CountUntil.Feedback()
        result = CountUntil.Result()
        counter = 0

        for _ in range(target):
            # Check for cancellation on every iteration, not just at the end.
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.reached_number = counter
                self.get_logger().info('goal canceled at %d' % counter)
                return result

            counter += 1
            feedback.current_number = counter
            goal_handle.publish_feedback(feedback)
            self.get_logger().info('counting: %d' % counter)
            time.sleep(period)

        # Exactly one terminal state must be set: succeed(), abort() or canceled().
        goal_handle.succeed()
        result.reached_number = counter
        self.get_logger().info('goal succeeded, reached %d' % counter)
        return result


def main(args=None):
    rclpy.init(args=args)
    node = CountUntilServer()
    executor = MultiThreadedExecutor()
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
