# Exercise 01 — Your first node

**After:** [lesson 03 — Nodes](../docs/03-nodes.md)

---

## The task

Write a node called `robot_news_station` that logs a message twice per second.

### Requirements

1. The node's name is `robot_news_station`.
2. It uses a **timer** (not a `while` loop, not `time.sleep`).
3. It logs `Hi, this is <robot_name> from the robot news station` every 0.5 s.
4. `<robot_name>` is a plain Python attribute for now — hard-code `"C3PO"`.
5. It also counts how many messages it has sent, and logs a `warn` every tenth
   one.
6. Ctrl+C shuts it down cleanly, with no traceback.

### Check yourself

```bash
ros2 run my_exercises robot_news_station
```

In another terminal:

```bash
ros2 node list                       # /robot_news_station must appear
ros2 node info /robot_news_station
```

---

## Hints

<details>
<summary>Hint 1 — the four steps</summary>

Every rclpy program does the same four things: `rclpy.init()`, create the
node, `rclpy.spin(node)`, `rclpy.shutdown()`.

</details>

<details>
<summary>Hint 2 — the timer</summary>

```python
self._timer = self.create_timer(0.5, self.publish_news)
```

Keep the reference in `self.` — a timer that gets garbage collected stops
firing.

</details>

<details>
<summary>Hint 3 — clean Ctrl+C</summary>

Wrap `rclpy.spin(node)` in `try/except KeyboardInterrupt` and do the cleanup
in a `finally` block.

</details>

---

## Solution

`my_exercises/my_exercises/robot_news_station.py`:

```python
#!/usr/bin/env python3
"""Exercise 01 - a node with a timer."""

import rclpy
from rclpy.node import Node


class RobotNewsStation(Node):
    """Logs a news bulletin twice per second."""

    def __init__(self):
        super().__init__('robot_news_station')

        self._robot_name = 'C3PO'
        self._count = 0

        # 0.5 seconds -> 2 Hz. Keep the reference in self.
        self._timer = self.create_timer(0.5, self.publish_news)

        self.get_logger().info('robot_news_station has started')

    def publish_news(self):
        self._count += 1

        self.get_logger().info(
            'Hi, this is %s from the robot news station' % self._robot_name)

        if self._count % 10 == 0:
            self.get_logger().warn('%d bulletins sent' % self._count)


def main(args=None):
    rclpy.init(args=args)
    node = RobotNewsStation()
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

`setup.py`:

```python
    entry_points={
        'console_scripts': [
            'robot_news_station = my_exercises.robot_news_station:main',
        ],
    },
```

Build and run:

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-select my_exercises
source install/setup.bash
ros2 run my_exercises robot_news_station
```

---

## Why it is written this way

**A timer, not a loop.** `rclpy.spin(node)` needs control of the thread so it
can dispatch callbacks. A `while True` loop in `__init__` would never give it
back, and the node would be unable to do anything else ever again — no
subscriptions, no services, no parameters. Lesson 11 goes deeper.

**`self._timer =`, not just `create_timer(...)`.** Python garbage-collects
objects nobody references. A dropped timer silently stops firing — a
confusing bug with no error message.

**`self.get_logger()`, not `print()`.** Logs carry the node name and
timestamp, can be filtered by severity, and appear in `rqt_console` and launch
log files.

**`try/except KeyboardInterrupt`.** Without it, Ctrl+C prints a traceback that
looks like a crash. With it, the node exits quietly.

---

## Going further

- Run two of them at once with different names:
  ```bash
  ros2 run my_exercises robot_news_station --ros-args -r __node:=station_2
  ```
  Look at `ros2 node list`. This is why node names are overridable.
- Switch a log line to `self.get_logger().debug(...)` and show it with
  `--ros-args --log-level debug`.
- Add `throttle_duration_sec=2.0` to the info log and watch the rate change
  without touching the timer.

**Next:** [Exercise 02 — publisher and subscriber](02-publisher-subscriber.md)
