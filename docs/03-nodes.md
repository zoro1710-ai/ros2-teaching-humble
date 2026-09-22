# 03 — Nodes

**Goal:** write a node from scratch, and use timers and logging the way ROS 2
expects.

**Code:** [`minimal_node.py`](../src/ros2_basics_py/ros2_basics_py/minimal_node.py),
[`timer_node.py`](../src/ros2_basics_py/ros2_basics_py/timer_node.py)

---

## Every rclpy program, in four steps

```python
import rclpy
from rclpy.node import Node


class MinimalNode(Node):
    def __init__(self):
        super().__init__('minimal_node')     # 2. the node's default name
        self.get_logger().info('hello')


def main(args=None):
    rclpy.init(args=args)                    # 1. connect to the middleware
    node = MinimalNode()
    rclpy.spin(node)                         # 3. hand control to ROS
    node.destroy_node()
    rclpy.shutdown()                         # 4. clean up
```

Run it:

```bash
ros2 run ros2_basics_py minimal_node
```

### What `spin()` really does

`rclpy.spin(node)` is a loop:

```
forever:
    wait until some callback is ready (a message arrived, a timer expired,
                                       a service request came in)
    run that callback
```

That is the whole execution model. Your code runs **only** inside callbacks.
A node with no callbacks — like `minimal_node` — just sits there, which is
fine; it still appears in `ros2 node list`.

The consequence you must internalise: **anything slow inside a callback stops
every other callback in that node.** Lesson 11 covers what to do about it.

---

## Timers: how to do periodic work

Never do this:

```python
while True:                     # WRONG - spin() never gets to run
    do_something()
    time.sleep(1.0)
```

Do this:

```python
self._timer = self.create_timer(0.5, self.on_timer)   # 0.5 s = 2 Hz

def on_timer(self):
    do_something()
```

Keep a reference (`self._timer`). If you let it be garbage collected, the
timer stops. The same applies to publishers, subscriptions and services.

Timers can be cancelled and recreated at runtime, which is how
[`parameter_demo.py`](../src/ros2_basics_py/ros2_basics_py/parameter_demo.py)
changes its own rate:

```python
self._timer.cancel()
self._timer = self.create_timer(1.0 / new_frequency, self.on_timer)
```

---

## Logging

Use the node's logger, never `print()`. The logger carries the node name, a
timestamp and a severity, goes to `/rosout` as well as the console, and can be
filtered at runtime.

```python
self.get_logger().debug('detailed internals')
self.get_logger().info('normal operation')
self.get_logger().warn('something is off but we continue')
self.get_logger().error('this operation failed')
self.get_logger().fatal('the node cannot continue')
```

`INFO` and above are shown by default. To see debug output:

```bash
ros2 run ros2_basics_py timer_node --ros-args --log-level timer_node:=debug
```

For something inside a fast loop, throttle it instead of flooding the console:

```python
self.get_logger().info('still waiting', throttle_duration_sec=2.0)
```

---

## Time

```python
now = self.get_clock().now()          # ROS time
stamp = now.to_msg()                  # builtin_interfaces/Time, for headers
seconds = now.nanoseconds / 1e9
```

Use `self.get_clock().now()`, not `time.time()`. When a simulator is driving
the clock (`use_sim_time:=true`), ROS time follows the simulation and wall
time does not — code written against `time.time()` silently breaks in
simulation.

---

## Naming and remapping

The name in `super().__init__('talker')` is a *default*. It can be changed
without touching the code:

```bash
ros2 run ros2_basics_py talker --ros-args -r __node:=talker_left
ros2 run ros2_basics_py talker --ros-args -r __ns:=/left
```

Two nodes with the same name at the same time is legal but confusing —
`ros2 node list` will show duplicates and tools get unreliable. Rename one.

---

## The complete code

Here is [`timer_node.py`](../src/ros2_basics_py/ros2_basics_py/timer_node.py)
in full, with nothing left out. Everything else in this course is a variation
on this shape.

```python
#!/usr/bin/env python3
"""Lesson 03 - timers, the ROS 2 way to do periodic work."""

import rclpy
from rclpy.node import Node


class TimerNode(Node):
    """Fires a callback twice per second and demonstrates the log levels."""

    def __init__(self):
        super().__init__('timer_node')
        self._tick = 0

        # create_timer(period_in_seconds, callback)
        self._timer = self.create_timer(0.5, self.on_timer)

        self.get_logger().info('timer_node started, ticking every 0.5 s')

    def on_timer(self):
        self._tick += 1

        # The five severity levels. Only INFO and above are printed by default;
        # show DEBUG with:  --ros-args --log-level timer_node:=debug
        self.get_logger().debug('debug: internal counter is %d' % self._tick)
        self.get_logger().info('tick %d' % self._tick)

        if self._tick % 10 == 0:
            self.get_logger().warn('ten ticks elapsed')

        # get_clock().now() is ROS time; it respects /clock when use_sim_time
        # is true, unlike time.time().
        if self._tick == 1:
            stamp = self.get_clock().now()
            self.get_logger().info('first tick at t=%.3f s' % (stamp.nanoseconds / 1e9))


def main(args=None):
    rclpy.init(args=args)
    node = TimerNode()
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

Line by line:

| Line | What it does |
|---|---|
| `import rclpy` | the ROS 2 Python client library |
| `from rclpy.node import Node` | the base class every node inherits |
| `class TimerNode(Node)` | your node **is a** Node — that is how it gets `create_timer`, `get_logger`, and the rest |
| `super().__init__('timer_node')` | registers the node with ROS under this default name. Nothing works before this line |
| `self._tick = 0` | ordinary Python state. Nothing special about it |
| `self._timer = self.create_timer(...)` | asks ROS to call `on_timer` every 0.5 s. **Stored on `self`** so it is not garbage collected |
| `def on_timer(self)` | the callback. Takes no arguments, returns nothing |
| `self.get_logger().info(...)` | logs with the node name, timestamp and severity attached |
| `rclpy.init(args=args)` | connect to the middleware. Exactly once per process |
| `node = TimerNode()` | construct it — which runs `__init__` and creates the timer |
| `rclpy.spin(node)` | hand the thread to ROS so callbacks can fire. Blocks until shutdown |
| `except KeyboardInterrupt` | Ctrl+C exits quietly instead of printing a traceback |
| `node.destroy_node()` | release the node's resources |
| `if rclpy.ok(): rclpy.shutdown()` | disconnect. The `ok()` guard avoids a double-shutdown error |
| `if __name__ == '__main__'` | lets you run the file directly with `python3`, as well as via `ros2 run` |

The `main()` block is identical in almost every file in this repo. Read it
once here, and from lesson 04 onwards you can skip straight to the class.

---

## Try it

```bash
# terminal 1
ros2 run ros2_basics_py timer_node

# terminal 2
ros2 node list
ros2 node info /timer_node
ros2 topic echo /rosout           # the log messages, as a topic
```

Then run it again with `--ros-args --log-level timer_node:=debug` and watch
the extra line appear.

---

## Common mistakes

**The node exits immediately.**
You forgot `rclpy.spin(node)`.

**A timer or subscription never fires.**
You did not store it on `self`, so Python garbage-collected it.

**`rclpy.init()` called twice.**
Usually caused by calling `main()` from a test that already called `init()`.
Guard with `rclpy.ok()`.

**Ctrl+C prints a long traceback.**
Wrap `spin()` in `try/except KeyboardInterrupt`, as every example in this repo
does.

---

## Exercise

[Exercise 01 — your first node](../exercises/01-first-node.md)

**Next:** [04 — Topics](04-topics.md)
