# Exercise 07 — An action

**After:** [lesson 09 — Actions](../docs/09-actions.md)

---

## The task

A long job with progress reporting and cancellation: moving a (simulated)
robot arm to a target angle.

### Requirements

**The interface** — `my_interfaces/action/MoveJoint.action`:

```
float64 target_angle      # degrees
float64 speed             # degrees per second
---
float64 final_angle       # where it actually ended up
bool reached_target
---
float64 current_angle     # progress
float64 percent_complete
```

**The server** — `joint_mover`:

1. Holds a current angle, starting at `0.0`.
2. **Rejects** a goal where `target_angle` is outside −180…180, or `speed` is
   ≤ 0 or > 90.
3. Moves towards the target in small steps, publishing feedback each step.
4. Supports cancellation, returning the angle it actually reached.
5. Must stay responsive while moving.

**The client** — `joint_mover_client`:

1. Parameters `target` (default `90.0`), `speed` (default `30.0`),
   `cancel_after` (default `0.0`, meaning never).
2. Sends the goal, logs feedback, checks whether it was accepted, reports the
   final status.

### Check yourself

```bash
ros2 run my_exercises joint_mover
```

```bash
ros2 action list
ros2 action info /move_joint -t
ros2 action send_goal /move_joint my_interfaces/action/MoveJoint \
    "{target_angle: 90.0, speed: 30.0}" --feedback

# rejected
ros2 action send_goal /move_joint my_interfaces/action/MoveJoint \
    "{target_angle: 400.0, speed: 30.0}"
```

```bash
ros2 run my_exercises joint_mover_client --ros-args -p target:=120.0 -p cancel_after:=1.5
```

---

## Hints

<details>
<summary>Hint 1 — registering the action file</summary>

`CMakeLists.txt` in `my_interfaces`:

```cmake
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MotorStatus.msg"
  "srv/SetSpeed.srv"
  "action/MoveJoint.action"
)
```

Then rebuild **and re-source**.

</details>

<details>
<summary>Hint 2 — the three server callbacks</summary>

```python
ActionServer(self, MoveJoint, 'move_joint',
             goal_callback=...,        # accept or reject
             cancel_callback=...,      # allow cancelling
             execute_callback=...,     # do the work
             callback_group=ReentrantCallbackGroup())
```

</details>

<details>
<summary>Hint 3 — why cancellation would not work</summary>

`execute()` blocks while it steps. On a single-threaded executor the cancel
request could never be processed. You need **both**
`ReentrantCallbackGroup` and `MultiThreadedExecutor`.

</details>

<details>
<summary>Hint 4 — cancellation is cooperative</summary>

Nobody interrupts your function. Check `goal_handle.is_cancel_requested`
inside the loop, every iteration.

</details>

<details>
<summary>Hint 5 — the client's feedback wrapper</summary>

It is `feedback_msg.feedback.current_angle`, not
`feedback_msg.current_angle`.

</details>

---

## Solution

### `my_interfaces/action/MoveJoint.action`

```
# Goal: where to move to, and how fast.
float64 target_angle      # degrees, -180 to 180
float64 speed             # degrees per second, 0 to 90
---
# Result: where the joint actually ended up.
float64 final_angle
bool reached_target
---
# Feedback: sent continuously while moving.
float64 current_angle
float64 percent_complete
```

### `my_exercises/my_exercises/joint_mover.py`

```python
#!/usr/bin/env python3
"""Exercise 07 - an action server with feedback and cancellation."""

import time

from my_interfaces.action import MoveJoint
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

STEP_PERIOD = 0.1          # seconds between feedback updates
MAX_SPEED = 90.0           # degrees per second
ANGLE_LIMIT = 180.0        # degrees


class JointMover(Node):
    """Moves a simulated joint to a target angle."""

    def __init__(self):
        super().__init__('joint_mover')

        self._current_angle = 0.0

        self._action_server = ActionServer(
            self,
            MoveJoint,
            'move_joint',
            goal_callback=self.on_goal_request,
            cancel_callback=self.on_cancel_request,
            execute_callback=self.execute,
            # Reentrant + MultiThreadedExecutor, or cancel can never be heard
            # while execute() is running.
            callback_group=ReentrantCallbackGroup())

        self.get_logger().info('move_joint action server ready at 0.0 deg')

    def on_goal_request(self, goal_request):
        """Validate before any work starts."""
        if abs(goal_request.target_angle) > ANGLE_LIMIT:
            self.get_logger().warn(
                'rejecting goal: target_angle %.1f is outside +/-%.0f'
                % (goal_request.target_angle, ANGLE_LIMIT))
            return GoalResponse.REJECT

        if not 0.0 < goal_request.speed <= MAX_SPEED:
            self.get_logger().warn(
                'rejecting goal: speed must be in (0, %.0f]' % MAX_SPEED)
            return GoalResponse.REJECT

        self.get_logger().info(
            'accepted goal: move to %.1f deg at %.1f deg/s'
            % (goal_request.target_angle, goal_request.speed))
        return GoalResponse.ACCEPT

    def on_cancel_request(self, goal_handle):
        self.get_logger().info('cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        target = goal_handle.request.target_angle
        speed = goal_handle.request.speed

        start = self._current_angle
        total = abs(target - start)
        direction = 1.0 if target > start else -1.0
        step = speed * STEP_PERIOD

        feedback = MoveJoint.Feedback()
        result = MoveJoint.Result()

        while abs(target - self._current_angle) > 0.001:
            # Cancellation is cooperative: nobody interrupts us, we look.
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.final_angle = self._current_angle
                result.reached_target = False
                self.get_logger().info(
                    'canceled at %.1f deg' % self._current_angle)
                return result

            remaining = abs(target - self._current_angle)
            self._current_angle += direction * min(step, remaining)

            feedback.current_angle = self._current_angle
            feedback.percent_complete = (
                100.0 if total == 0.0
                else 100.0 * (total - remaining) / total)
            goal_handle.publish_feedback(feedback)

            time.sleep(STEP_PERIOD)

        # Exactly one terminal state, then return a Result.
        goal_handle.succeed()
        result.final_angle = self._current_angle
        result.reached_target = True
        self.get_logger().info('reached %.1f deg' % self._current_angle)
        return result


def main(args=None):
    rclpy.init(args=args)
    node = JointMover()
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
```

### `my_exercises/my_exercises/joint_mover_client.py`

```python
#!/usr/bin/env python3
"""Exercise 07 - an action client, including cancellation."""

from action_msgs.msg import GoalStatus
from my_interfaces.action import MoveJoint
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

STATUS_NAMES = {
    GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
    GoalStatus.STATUS_ABORTED: 'ABORTED',
    GoalStatus.STATUS_CANCELED: 'CANCELED',
}


class JointMoverClient(Node):
    """Sends one MoveJoint goal and optionally cancels it part way."""

    def __init__(self):
        super().__init__('joint_mover_client')

        self.declare_parameter('target', 90.0)
        self.declare_parameter('speed', 30.0)
        self.declare_parameter('cancel_after', 0.0)   # 0.0 = never cancel

        self._target = self.get_parameter('target').value
        self._speed = self.get_parameter('speed').value
        self._cancel_after = self.get_parameter('cancel_after').value

        self._goal_handle = None
        self._cancel_timer = None

        self._action_client = ActionClient(self, MoveJoint, 'move_joint')
        self.send_goal()

    def send_goal(self):
        self.get_logger().info('waiting for the move_joint action server ...')
        self._action_client.wait_for_server()

        goal = MoveJoint.Goal()
        goal.target_angle = self._target
        goal.speed = self._speed

        self.get_logger().info(
            'sending goal: %.1f deg at %.1f deg/s' % (self._target, self._speed))

        # Step 1: this future resolves to a GOAL HANDLE, not to the result.
        future = self._action_client.send_goal_async(
            goal, feedback_callback=self.on_feedback)
        future.add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        self._goal_handle = future.result()

        # Step 2: the server may have rejected us. A rejected goal never
        # produces a result, so this check is not optional.
        if not self._goal_handle.accepted:
            self.get_logger().warn('goal was rejected by the server')
            rclpy.shutdown()
            return

        self.get_logger().info('goal accepted')

        if self._cancel_after > 0.0:
            self._cancel_timer = self.create_timer(
                self._cancel_after, self.cancel_goal)

        # Step 3: a second future, for the final result.
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self.on_result)

    def cancel_goal(self):
        self._cancel_timer.cancel()          # one-shot
        self.get_logger().info('asking the server to cancel')
        self._goal_handle.cancel_goal_async()

    def on_feedback(self, feedback_msg):
        # Feedback arrives WRAPPED - note the extra .feedback
        fb = feedback_msg.feedback
        self.get_logger().info(
            'at %.1f deg (%.0f%%)' % (fb.current_angle, fb.percent_complete))

    def on_result(self, future):
        wrapper = future.result()
        status = STATUS_NAMES.get(wrapper.status, 'UNKNOWN(%d)' % wrapper.status)
        self.get_logger().info(
            'status %s, final angle %.1f, reached_target=%s'
            % (status, wrapper.result.final_angle, wrapper.result.reached_target))
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = JointMoverClient()
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
```

`package.xml` of `my_exercises` needs `<depend>my_interfaces</depend>`, and
`setup.py` needs the two new entry points.

---

## Why it is written this way

**Validation lives in `goal_callback`, not in `execute`.** Rejecting before
any work starts means the client learns immediately, and no partial motion
happens. `execute` can then assume its inputs are sane.

**`is_cancel_requested` is checked every iteration.** Checking once at the top
would make cancellation useless. Cancellation in ROS 2 is cooperative — the
framework sets a flag, your code has to honour it.

**Every exit path sets a terminal state and returns a Result.** `succeed()`,
`abort()` or `canceled()` — exactly one, always followed by `return result`.
Miss it and the client hangs forever waiting for a result that never comes.

**`ReentrantCallbackGroup` + `MultiThreadedExecutor`, together.** Either alone
does nothing. The group says "these callbacks may overlap"; the executor
provides the threads to overlap them on. Without both, `execute()` blocks the
one thread and the cancel service request sits unprocessed in the queue.

**The client keeps `self._goal_handle`.** You cannot cancel without it, and it
only exists after `on_goal_response` runs.

**`wait_for_server()` is fine here.** This client does nothing else while it
waits — it is not inside a callback of a node with other work. That is the one
situation where blocking is acceptable.

---

## Going further

- Add a `min_angle`/`max_angle` parameter pair and reject goals outside them,
  so the limits are configurable rather than constants.
- Make the server **abort** if the target is unreachable partway through (say,
  a simulated collision at 150°) using `goal_handle.abort()`, and check that
  the client reports `ABORTED` and `reached_target=False`.
- Send a second goal while the first is running. By default both execute —
  decide whether that makes sense for a joint, and if not, track the active
  handle and abort the old one.

**Next:** [Exercise 08 — find the QoS bug](08-qos.md)
