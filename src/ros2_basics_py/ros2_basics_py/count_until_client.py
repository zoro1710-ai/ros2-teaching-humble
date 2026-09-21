#!/usr/bin/env python3
"""Lesson 09 - an action client, including cancellation.

Run the server first, then:
    ros2 run ros2_basics_py count_until_client
    ros2 run ros2_basics_py count_until_client --ros-args -p target:=10 -p cancel_after:=3.0

Sending a goal is a three-step asynchronous dance:
    1. send_goal_async()            -> future resolves with a goal handle
    2. goal_handle.accepted?        -> the server may have rejected you
    3. get_result_async()           -> future resolves with the final result

Feedback arrives independently on its own callback the whole time.
"""

from action_msgs.msg import GoalStatus
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from ros2_basics_interfaces.action import CountUntil

STATUS_NAMES = {
    GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
    GoalStatus.STATUS_ABORTED: 'ABORTED',
    GoalStatus.STATUS_CANCELED: 'CANCELED',
}


class CountUntilClient(Node):
    """Sends one CountUntil goal and optionally cancels it part way through."""

    def __init__(self):
        super().__init__('count_until_client')

        self.declare_parameter('target', 6)
        self.declare_parameter('period', 1.0)
        # 0.0 means "never cancel, let it run to completion".
        self.declare_parameter('cancel_after', 0.0)

        self._target = self.get_parameter('target').value
        self._period = self.get_parameter('period').value
        self._cancel_after = self.get_parameter('cancel_after').value

        self._goal_handle = None
        self._cancel_timer = None

        self._action_client = ActionClient(self, CountUntil, 'count_until')
        self.send_goal()

    def send_goal(self):
        self.get_logger().info('waiting for the count_until action server ...')
        self._action_client.wait_for_server()

        goal = CountUntil.Goal()
        goal.target_number = self._target
        goal.period = self._period

        self.get_logger().info(
            'sending goal: count to %d every %.2f s' % (self._target, self._period))

        future = self._action_client.send_goal_async(
            goal, feedback_callback=self.on_feedback)
        future.add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        self._goal_handle = future.result()

        if not self._goal_handle.accepted:
            self.get_logger().warn('goal was rejected by the server')
            rclpy.shutdown()
            return

        self.get_logger().info('goal accepted')

        if self._cancel_after > 0.0:
            self._cancel_timer = self.create_timer(self._cancel_after, self.cancel_goal)

        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self.on_result)

    def cancel_goal(self):
        self._cancel_timer.cancel()
        self.get_logger().info('asking the server to cancel')
        self._goal_handle.cancel_goal_async()

    def on_feedback(self, feedback_msg):
        self.get_logger().info(
            'feedback: currently at %d' % feedback_msg.feedback.current_number)

    def on_result(self, future):
        wrapper = future.result()
        status = STATUS_NAMES.get(wrapper.status, 'UNKNOWN(%d)' % wrapper.status)
        self.get_logger().info(
            'final status %s, reached %d' % (status, wrapper.result.reached_number))
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = CountUntilClient()
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
