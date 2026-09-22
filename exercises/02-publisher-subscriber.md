# Exercise 02 — Publisher and subscriber

**After:** [lesson 04 — Topics](../docs/04-topics.md)

---

## The task

Two nodes that talk over a topic.

### Requirements

**Node 1 — `counter_publisher`**

1. Publishes on the topic `counter` (relative name, no leading slash).
2. Message type `example_interfaces/msg/Int64`.
3. Starts at 0 and increments by 1 every second.

**Node 2 — `counter_subscriber`**

1. Subscribes to `counter`.
2. Logs `I heard: <value>` for every message.
3. Keeps a running total and logs it every tenth message.

### Check yourself

```bash
ros2 run my_exercises counter_publisher
ros2 run my_exercises counter_subscriber
```

```bash
ros2 topic list
ros2 topic echo /counter
ros2 topic hz /counter                     # should be ~1.0
ros2 topic info /counter --verbose         # 1 publisher, 1 subscriber
```

Then, without writing any extra code, prove each half works alone:

```bash
# feed the subscriber by hand
ros2 topic pub /counter example_interfaces/msg/Int64 "{data: 99}" --once
```

And rewire both nodes without editing them:

```bash
ros2 run my_exercises counter_publisher  --ros-args -r counter:=/robot/counter
ros2 run my_exercises counter_subscriber --ros-args -r counter:=/robot/counter
```

---

## Hints

<details>
<summary>Hint 1 — creating the publisher</summary>

```python
self._publisher = self.create_publisher(Int64, 'counter', 10)
```

Arguments: message type, topic name, queue depth.

</details>

<details>
<summary>Hint 2 — filling a message</summary>

You cannot do `Int64(5)`. Create it empty, then assign:

```python
msg = Int64()
msg.data = 5
```

</details>

<details>
<summary>Hint 3 — the subscription</summary>

```python
self._subscription = self.create_subscription(Int64, 'counter', self.on_message, 10)

def on_message(self, msg):
    ...
```

The callback receives the message, and returns nothing.

</details>

<details>
<summary>Hint 4 — if nothing arrives</summary>

Three things must match: the topic **name**, the message **type**, and the
**QoS**. `ros2 topic info /counter --verbose` shows all three for both sides.

</details>

---

## Solution

`my_exercises/my_exercises/counter_publisher.py`:

```python
#!/usr/bin/env python3
"""Exercise 02 - publishes an incrementing counter on /counter."""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node


class CounterPublisher(Node):
    """Publishes 0, 1, 2, ... once per second."""

    def __init__(self):
        super().__init__('counter_publisher')

        self._count = 0

        # (message type, topic name, queue depth)
        # 'counter' is relative, so it can be remapped and namespaced.
        self._publisher = self.create_publisher(Int64, 'counter', 10)
        self._timer = self.create_timer(1.0, self.publish_count)

        self.get_logger().info('publishing on /counter')

    def publish_count(self):
        msg = Int64()
        msg.data = self._count
        self._publisher.publish(msg)

        self.get_logger().info('published %d' % self._count)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = CounterPublisher()
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

`my_exercises/my_exercises/counter_subscriber.py`:

```python
#!/usr/bin/env python3
"""Exercise 02 - listens on /counter and keeps a running total."""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node


class CounterSubscriber(Node):
    """Prints every value received and the running total."""

    def __init__(self):
        super().__init__('counter_subscriber')

        self._total = 0
        self._received = 0

        self._subscription = self.create_subscription(
            Int64, 'counter', self.on_message, 10)

        self.get_logger().info('waiting for messages on /counter')

    def on_message(self, msg):
        self._received += 1
        self._total += msg.data

        self.get_logger().info('I heard: %d' % msg.data)

        if self._received % 10 == 0:
            self.get_logger().info(
                'running total after %d messages: %d' % (self._received, self._total))


def main(args=None):
    rclpy.init(args=args)
    node = CounterSubscriber()
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
            'counter_publisher = my_exercises.counter_publisher:main',
            'counter_subscriber = my_exercises.counter_subscriber:main',
        ],
    },
```

---

## Why it is written this way

**Relative topic names.** `'counter'` becomes `/counter`, but it can be
remapped to anything and it picks up namespaces. `'/counter'` is absolute and
ignores both — which breaks the moment you run two robots.

**The queue depth of 10.** That `10` is really a QoS profile meaning "keep the
last 10, reliable, volatile". Lesson 10 unpacks it.

**Nothing in the callback is slow.** The subscriber callback runs on the
executor thread. While it runs, nothing else in the node can. Keep it short —
store, compute cheaply, return.

**The subscriber has no loop.** It never asks for data. The executor calls
`on_message` once per arriving message. That inversion of control is the whole
ROS 2 programming model.

---

## Going further

- Start a **second** subscriber. Both receive every message — topics are
  many-to-many.
- Start a second publisher on the same topic. The subscriber gets both,
  interleaved. That is legal, and usually a bug.
- Change the publisher's queue depth to 1 and add `time.sleep(2)` in the
  subscriber's callback. Watch messages get dropped, and see how the depth
  controls it.

**Next:** [Exercise 03 — a service](03-service.md)
