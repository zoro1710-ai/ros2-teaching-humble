# 11 — Executors and callback groups

**Goal:** explain exactly why your node froze, and fix it.

**Code:** [`executor_demo.py`](../src/ros2_basics_py/ros2_basics_py/executor_demo.py)

---

## What `spin()` really is

You have written `rclpy.spin(node)` in every example. Here is what it does:

```
forever:
    wait until some callback is ready
        (a message arrived, a timer expired, a service request came in)
    run that callback
    repeat
```

That loop is the **executor**. Your code runs *only* inside callbacks, and by
default there is **one thread** running them, one at a time.

Which leads to the single most important consequence in ROS 2:

> **Anything slow inside a callback stops every other callback in that node.**

A 2-second `time.sleep()` in a timer callback means no messages are processed,
no services are answered, and no other timer fires for those 2 seconds.

---

## See it happen

[`executor_demo.py`](../src/ros2_basics_py/ros2_basics_py/executor_demo.py) has
two timers: a fast one every 0.25 s, and a slow one every 3 s that deliberately
blocks for 2 s.

```python
import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node


class ExecutorDemo(Node):
    """Two timers, one of which blocks, to make executor behaviour visible."""

    def __init__(self):
        super().__init__('executor_demo')

        self.declare_parameter('multi_threaded', False)
        self._multi_threaded = self.get_parameter('multi_threaded').value

        if self._multi_threaded:
            group = ReentrantCallbackGroup()
        else:
            group = MutuallyExclusiveCallbackGroup()

        self._fast_timer = self.create_timer(0.25, self.fast_tick, callback_group=group)
        self._slow_timer = self.create_timer(3.0, self.slow_tick, callback_group=group)
        self._fast_ticks = 0

    def fast_tick(self):
        self._fast_ticks += 1
        self.get_logger().info('fast tick %d' % self._fast_ticks)

    def slow_tick(self):
        self.get_logger().warn('slow callback START (blocking for 2 s)')
        time.sleep(2.0)
        self.get_logger().warn('slow callback END')


def main(args=None):
    rclpy.init(args=args)
    node = ExecutorDemo()

    if node.get_parameter('multi_threaded').value:
        executor = MultiThreadedExecutor(num_threads=4)
    else:
        executor = SingleThreadedExecutor()

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
```

Run the default version:

```bash
ros2 run ros2_basics_py executor_demo
```

```
[INFO] fast tick 10
[INFO] fast tick 11
[WARN] slow callback START (blocking for 2 s)      <- fast ticks stop here
[WARN] slow callback END
[INFO] fast tick 12                                 <- and resume here
```

The fast timer goes silent for two whole seconds. **That is what "my node
froze" looks like.**

Now the fixed version:

```bash
ros2 run ros2_basics_py executor_demo --ros-args -p multi_threaded:=true
```

```
[WARN] slow callback START (blocking for 2 s)
[INFO] fast tick 12
[INFO] fast tick 13                                 <- keeps ticking
[INFO] fast tick 14
[WARN] slow callback END
```

---

## The two pieces of the fix

Both are needed. Either one alone changes nothing.

### 1. A multi-threaded executor

```python
from rclpy.executors import MultiThreadedExecutor

executor = MultiThreadedExecutor(num_threads=4)
executor.add_node(node)
executor.spin()
```

This replaces `rclpy.spin(node)`. Now there are four threads available to run
callbacks — but by default they still will not run *your* callbacks
concurrently, because of the next piece.

### 2. The right callback group

Every callback belongs to a group, and the group decides what may overlap.

| Group | Behaviour |
|---|---|
| `MutuallyExclusiveCallbackGroup` | callbacks in this group never run at the same time as each other |
| `ReentrantCallbackGroup` | callbacks in this group may run concurrently, and even re-enter themselves |

**Every node has a default mutually-exclusive group**, and every callback goes
into it unless you say otherwise. That is why a `MultiThreadedExecutor` alone
does nothing: all your callbacks are still in one exclusive group.

```python
group = ReentrantCallbackGroup()
self.create_timer(0.25, self.fast_tick, callback_group=group)
self.create_timer(3.0, self.slow_tick, callback_group=group)
```

`callback_group=` is accepted by `create_timer`, `create_subscription`,
`create_service`, `create_client`, `ActionServer` and `ActionClient`.

### The useful middle ground

Full reentrancy is not always what you want — concurrent callbacks touching
the same variable is a data race, and you now need locks.

A common, safer pattern is **one mutually-exclusive group per concern**:

```python
self._sensor_group = MutuallyExclusiveCallbackGroup()
self._service_group = MutuallyExclusiveCallbackGroup()

self.create_subscription(Image, 'image', self.on_image, 10,
                         callback_group=self._sensor_group)
self.create_service(Trigger, 'do_thing', self.on_request,
                    callback_group=self._service_group)
```

Different groups run in parallel; callbacks within a group are still
serialised, so each group's own state is safe without locks.

---

## The deadlock you will eventually hit

This is why [lesson 05](05-services.md) told you never to use the blocking
`client.call()` inside a callback:

```python
def on_timer(self):                       # runs on the executor thread
    response = self._client.call(request) # waits for the response ...
    # ... but the response can only be processed by the executor thread,
    # which is right here, waiting. Deadlock. The node hangs forever.
```

The same trap applies to `wait_for_service()` without a timeout, and to
`spin_until_future_complete()` called from inside a callback.

Three ways out, in order of preference:

1. **`call_async()` + `add_done_callback()`** — the pattern used throughout
   this repo. No blocking at all. Prefer this.
2. A **`ReentrantCallbackGroup`** plus a `MultiThreadedExecutor`, so another
   thread can process the response while this one waits.
3. Do the blocking work in your own `threading.Thread` and hand the result
   back — for genuinely long CPU or I/O work.

The action server in [lesson 09](09-actions.md) is a real example of option 2:
its `execute()` blocks, so it needs `ReentrantCallbackGroup` +
`MultiThreadedExecutor` or cancellation could never be processed.

---

## Several nodes on one executor

An executor is not limited to one node. This runs two nodes in one process,
which is common in tests and small applications:

```python
    executor = SingleThreadedExecutor()
    executor.add_node(publisher_node)
    executor.add_node(counter_node)
    executor.spin()
```

You can see exactly this in
[`test_talker_listener.py`](../src/ros2_basics_py/test/test_talker_listener.py).

Remember they then share the executor's threads — a slow callback in one node
blocks the other.

---

## Try it

```bash
# the freeze
ros2 run ros2_basics_py executor_demo

# the fix
ros2 run ros2_basics_py executor_demo --ros-args -p multi_threaded:=true
```

Then edit `executor_demo.py` and try the third combination yourself:
`MultiThreadedExecutor` with `MutuallyExclusiveCallbackGroup`. The fast timer
still freezes — proving that the executor alone is not the fix.

---

## Common mistakes

**"I switched to MultiThreadedExecutor and nothing changed."**
Your callbacks are still all in the default mutually-exclusive group. Pass
`callback_group=ReentrantCallbackGroup()` (or separate groups).

**`time.sleep()` in a callback.**
Almost always wrong. Use a timer, or restructure into a state machine.

**A `while` loop in a callback waiting for something.**
Same problem. Whatever you are waiting for probably arrives via another
callback that can never run.

**Blocking `client.call()` inside any callback.**
Deadlock. Use `call_async()` + `add_done_callback()`.

**Race conditions after switching to reentrant groups.**
Now real. Either protect shared state with `threading.Lock`, or use separate
mutually-exclusive groups so each piece of state has one owner.

**`rclpy.spin(node)` *and* `executor.spin()`.**
Pick one. `rclpy.spin(node)` creates its own single-threaded executor
internally.

---

## Recap

- `spin()` = a loop that runs ready callbacks. One thread by default.
- A slow callback blocks everything else in the node.
- Concurrency needs **both** a `MultiThreadedExecutor` **and** a
  non-default callback group.
- `ReentrantCallbackGroup` = may overlap. `MutuallyExclusiveCallbackGroup` =
  never overlaps with itself; different groups still run in parallel.
- Never block inside a callback. `call_async` + done-callback is the way.

**Next:** [12 — TF2](12-tf2.md)
