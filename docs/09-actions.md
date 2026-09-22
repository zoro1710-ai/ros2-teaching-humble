# 09 — Actions

**Goal:** handle work that takes a long time, reports progress, and can be
cancelled.

**Code:** [`CountUntil.action`](../src/ros2_basics_interfaces/action/CountUntil.action),
[`count_until_server.py`](../src/ros2_basics_py/ros2_basics_py/count_until_server.py),
[`count_until_client.py`](../src/ros2_basics_py/ros2_basics_py/count_until_client.py)

---

## When a service is not enough

A service is *"ask a question, get an answer"*. It works when the answer comes
back in milliseconds.

Now imagine asking a robot to **navigate to the kitchen**. That takes 40
seconds. With a service you would:

- block the caller for 40 seconds,
- get no progress updates,
- have no way to change your mind halfway.

That is what actions are for. Use one when **any** of these is true:

| | Topic | Service | Action |
|---|---|---|---|
| takes a long time | — | ✗ | ✓ |
| caller wants progress | — | ✗ | ✓ |
| caller may cancel | — | ✗ | ✓ |
| one-way data stream | ✓ | — | — |
| quick question/answer | — | ✓ | — |

Under the hood, an action is **three services + two topics**:

```
send_goal    (service)   client -> server   "please do this"
cancel_goal  (service)   client -> server   "stop"
get_result   (service)   client -> server   "what happened?"
feedback     (topic)     server -> client   "I am at step 3 of 10"
status       (topic)     server -> client   goal state machine
```

You never touch those directly — `ActionServer` and `ActionClient` hide them.
But knowing this explains why `ros2 action info /count_until -t` prints five
things.

---

## The .action file

Three sections, separated by `---`:

[`action/CountUntil.action`](../src/ros2_basics_interfaces/action/CountUntil.action):

```
# Goal: count from 1 up to target_number, waiting `period` seconds between steps.
int64 target_number
float64 period
---
# Result: the last number actually reached.
int64 reached_number
---
# Feedback: the number we are currently on.
int64 current_number
```

In Python those become `CountUntil.Goal`, `CountUntil.Result` and
`CountUntil.Feedback`. Register the file in `CMakeLists.txt` exactly like a
message ([lesson 06](06-custom-interfaces.md)).

---

## The server

Full file —
[`count_until_server.py`](../src/ros2_basics_py/ros2_basics_py/count_until_server.py):

```python
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
```

### The three callbacks

**`goal_callback`** runs first, for every incoming goal. Return
`GoalResponse.ACCEPT` or `GoalResponse.REJECT`. This is your validation gate —
reject nonsense here, before any work starts. It receives the goal *message*,
not a handle.

**`cancel_callback`** runs when the client asks to cancel. Return
`CancelResponse.ACCEPT` or `REJECT`. Almost always accept: refusing to stop is
rarely what anyone wants.

**`execute_callback`** does the work. It receives a `goal_handle`, and:

- `goal_handle.request` is the goal you were sent,
- `goal_handle.publish_feedback(feedback)` sends progress,
- `goal_handle.is_cancel_requested` tells you a cancel arrived,
- exactly one of `succeed()`, `abort()` or `canceled()` must be called,
- it must **return a Result object** — even when cancelled or aborted.

Forgetting the terminal state leaves the client waiting forever, and rclpy
logs a warning about a goal that never reached a terminal state.

### Why the cancel check is inside the loop

```python
        for _ in range(target):
            if goal_handle.is_cancel_requested:
                ...
```

Cancellation is **cooperative**. Nobody interrupts your function; you have to
look. Check once per iteration of whatever loop is doing the work.

### Why MultiThreadedExecutor

`execute()` blocks in `time.sleep(period)`. With the default single-threaded
executor, the cancel request arriving during that sleep could never be
processed — the executor is busy running `execute()`.

So this node uses:

- `callback_group=ReentrantCallbackGroup()` — these callbacks may overlap,
- `MultiThreadedExecutor()` — there are threads available to overlap them.

Both are needed; one without the other does nothing.
[Lesson 11](11-executors-and-callback-groups.md) explains this properly.

---

## The client

Sending a goal is a three-step asynchronous dance. From
[`count_until_client.py`](../src/ros2_basics_py/ros2_basics_py/count_until_client.py):

```python
    def send_goal(self):
        self.get_logger().info('waiting for the count_until action server ...')
        self._action_client.wait_for_server()

        goal = CountUntil.Goal()
        goal.target_number = self._target
        goal.period = self._period

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
```

Step by step:

1. **`send_goal_async(goal, feedback_callback=...)`** returns a future that
   resolves to a **goal handle** — *not* the result. All it means is "the
   server has seen your goal".
2. **`goal_handle.accepted`** — check it. The server's `goal_callback` may
   have rejected you, and a rejected goal never produces a result.
3. **`goal_handle.get_result_async()`** returns a second future, which
   resolves when the work finishes.

Two details that confuse people:

- The feedback callback receives a **wrapper**, so it is
  `feedback_msg.feedback.current_number`, not `feedback_msg.current_number`.
- The result callback also receives a wrapper: `wrapper.status` (from
  `action_msgs/GoalStatus`) and `wrapper.result` (your `CountUntil.Result`).
  Always check the status — an aborted goal still delivers a result object,
  full of default values.

The status constants worth knowing:

```python
GoalStatus.STATUS_SUCCEEDED   # finished normally
GoalStatus.STATUS_ABORTED     # the server gave up (abort() was called)
GoalStatus.STATUS_CANCELED    # cancelled, and the server confirmed
```

Cancelling is just `goal_handle.cancel_goal_async()` on the handle you kept
from step 2. Keep that handle — you cannot cancel without it.

---

## Try it

```bash
# terminal 1
ros2 run ros2_basics_py count_until_server
```

Drive it entirely from the CLI first:

```bash
# terminal 2
ros2 action list
ros2 action info /count_until -t
ros2 interface show ros2_basics_interfaces/action/CountUntil

ros2 action send_goal /count_until ros2_basics_interfaces/action/CountUntil \
    "{target_number: 5, period: 1.0}" --feedback
```

`--feedback` is what makes the progress stream visible. Without it you only
see the final result.

Now the rejection path:

```bash
ros2 action send_goal /count_until ros2_basics_interfaces/action/CountUntil \
    "{target_number: -3, period: 1.0}"
```

Then the Python client, including cancellation:

```bash
ros2 run ros2_basics_py count_until_client
ros2 run ros2_basics_py count_until_client --ros-args -p target:=10 -p cancel_after:=3.0
```

The second command sends a goal that would take 10 seconds and cancels it
after 3. Watch both terminals: the server logs `cancel requested`, stops
counting, and reports `CANCELED` with the number it actually reached.

---

## Common mistakes

**The client hangs forever after the goal is accepted.**
The server's `execute()` never called `succeed()`, `abort()` or `canceled()`,
or never returned a Result.

**Cancel does nothing.**
Either `execute()` never checks `is_cancel_requested`, or the node is on a
single-threaded executor and cannot process the cancel service while
`execute()` runs. You need `ReentrantCallbackGroup` **and**
`MultiThreadedExecutor`.

**`AttributeError: 'CountUntil_FeedbackMessage' object has no attribute 'current_number'`**
Use `feedback_msg.feedback.current_number`.

**You get a result full of zeros.**
The goal was aborted or rejected. Check `wrapper.status` before trusting
`wrapper.result`.

**`AttributeError: 'NoneType' object has no attribute 'cancel_goal_async'`**
You tried to cancel before `on_goal_response` stored the handle.

**The server accepts a second goal and the first one's results get confusing.**
By default a new goal does not stop the old one. If only one goal at a time
makes sense for your robot, track the active handle and abort it yourself, or
use `ActionServer`'s goal-handling options.

---

## Recap

- Action = long task + feedback + cancellation. Built from 3 services and
  2 topics; the class hides that.
- `.action` file: goal `---` result `---` feedback.
- Server: `goal_callback` (accept/reject), `cancel_callback`,
  `execute_callback` (publish feedback, check `is_cancel_requested`, set a
  terminal state, return a Result).
- A blocking `execute()` needs `ReentrantCallbackGroup` +
  `MultiThreadedExecutor` or cancellation cannot work.
- Client: `send_goal_async` → check `.accepted` → `get_result_async` →
  check `.status`.

## Exercise

[Exercise 07 — write an action](../exercises/07-action.md)

**Next:** [10 — Quality of Service](10-qos.md)
