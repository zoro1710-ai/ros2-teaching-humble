# 04 — Topics

**Goal:** publish, subscribe, and debug a topic entirely from the command line.

**Code:** [`talker.py`](../src/ros2_basics_py/ros2_basics_py/talker.py),
[`listener.py`](../src/ros2_basics_py/ros2_basics_py/listener.py),
[`number_publisher.py`](../src/ros2_basics_py/ros2_basics_py/number_publisher.py),
[`number_counter.py`](../src/ros2_basics_py/ros2_basics_py/number_counter.py)

---

## The model

A topic is a named, typed, many-to-many stream.

```
        /chatter  (std_msgs/String)
talker  ───────────────────────────>  listener
                                 └──>  another_listener
```

The publisher does not know who is listening, does not block, and gets no
acknowledgement. If nobody is subscribed, messages go nowhere and that is not
an error.

Three things must match or the two sides will never connect:

1. the **topic name**
2. the **message type**
3. the **QoS profile** ([lesson 10](10-qos.md))

---

## Publishing

```python
from std_msgs.msg import String

self._publisher = self.create_publisher(String, 'chatter', 10)

msg = String()
msg.data = 'hello'
self._publisher.publish(msg)
```

The `10` is shorthand for a queue depth of 10 with the default reliable
profile.

**The name has no leading slash.** `'chatter'` is a *relative* name, which
becomes `/chatter` — or `/left/chatter` if the node runs in the `/left`
namespace. Writing `'/chatter'` makes it absolute and immune to namespacing,
which breaks multi-robot setups. Default to relative names.

## Subscribing

```python
self._subscription = self.create_subscription(
    String, 'chatter', self.on_message, 10)

def on_message(self, msg):
    self.get_logger().info(msg.data)
```

The callback runs on the executor thread. Keep it short.

---

## Choosing a message type

Look before you invent. Most of what you need already exists:

| Package | Examples |
|---|---|
| `std_msgs` | `String`, `Bool`, `Float64`, `Header` |
| `geometry_msgs` | `Twist` (velocity), `Pose`, `Point`, `TransformStamped` |
| `sensor_msgs` | `Image`, `LaserScan`, `Imu`, `JointState`, `PointCloud2` |
| `nav_msgs` | `Odometry`, `Path`, `OccupancyGrid` |
| `example_interfaces` | `Int64`, `String` — for tutorials only |

```bash
ros2 interface list
ros2 interface show geometry_msgs/msg/Twist
ros2 interface packages
```

Using a standard type means existing tools (RViz, rqt, rosbag) understand your
data for free. `std_msgs/String` for structured data is an anti-pattern — if
you are packing several values into one string, define a message
([lesson 06](06-custom-interfaces.md)).

---

## The complete code

### The publisher

[`talker.py`](../src/ros2_basics_py/ros2_basics_py/talker.py), in full:

```python
#!/usr/bin/env python3
"""Lesson 04 - the classic publisher."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    """Publishes an incrementing greeting on /chatter."""

    def __init__(self):
        super().__init__('talker')

        # create_publisher(msg_type, topic_name, qos)
        # The plain integer 10 is shorthand for "keep last 10, reliable".
        self._publisher = self.create_publisher(String, 'chatter', 10)
        self._count = 0
        self._timer = self.create_timer(0.5, self.publish_message)

        self.get_logger().info('talker publishing on /chatter')

    def publish_message(self):
        msg = String()
        msg.data = 'Hello ROS 2: %d' % self._count
        self._publisher.publish(msg)
        self.get_logger().info('published "%s"' % msg.data)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
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

Compared with `timer_node.py` from [lesson 03](03-nodes.md), exactly three
things are new:

1. `from std_msgs.msg import String` — the message **type**. The import path
   for any message is `<package>.msg`.
2. `self._publisher = self.create_publisher(String, 'chatter', 10)` — creates
   the publisher. Store it on `self`, like the timer.
3. Inside the callback: build a message, fill its fields, publish it.

The three-step message dance is worth saying out loud, because you cannot
shortcut it:

```python
msg = String()          # create it empty
msg.data = 'hello'      # fill each field by name
self._publisher.publish(msg)
```

`String('hello')` does not work. Neither does publishing a raw Python string.

### The subscriber

[`listener.py`](../src/ros2_basics_py/ros2_basics_py/listener.py), in full:

```python
#!/usr/bin/env python3
"""Lesson 04 - the classic subscriber."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    """Prints every message received on /chatter."""

    def __init__(self):
        super().__init__('listener')

        # create_subscription(msg_type, topic_name, callback, qos)
        # The topic name, type and QoS must all match the publisher or the
        # two will never connect.
        self._subscription = self.create_subscription(
            String, 'chatter', self.on_message, 10)

        self.get_logger().info('listener waiting for messages on /chatter')

    def on_message(self, msg):
        self.get_logger().info('heard "%s"' % msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
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

Notice what is **not** here: there is no loop, no `get_message()`, no polling.
The subscriber never asks for data. You register `on_message` and the executor
calls it once per arriving message.

That inversion — your code is called, it does not call — is the ROS 2
programming model. Everything from here on is more of it.

`on_message(self, msg)` takes exactly one argument (the message) and returns
nothing. Whatever it returns is discarded.

---

## Debugging from the CLI

This is the most valuable habit in this lesson.

```bash
ros2 topic list                       # what exists
ros2 topic list -t                    # ... with types
ros2 topic info /chatter --verbose    # publishers, subscribers, and QoS
ros2 topic echo /chatter              # print the data
ros2 topic hz /chatter                # actual publishing rate
ros2 topic bw /chatter                # bandwidth
ros2 topic pub /chatter std_msgs/msg/String "{data: 'test'}" --once
ros2 topic delay /scan                # latency, needs a Header
```

`ros2 topic pub` is how you test a subscriber without writing a publisher, and
`ros2 topic echo` is how you test a publisher without writing a subscriber.
You can build and debug half a system before the other half exists.

---

## Try it

### The talker and the listener

```bash
# terminal 1
ros2 run ros2_basics_py talker
# terminal 2
ros2 run ros2_basics_py listener
# terminal 3
ros2 topic info /chatter --verbose
```

Now inject a message by hand and watch the listener pick it up:

```bash
ros2 topic pub /chatter std_msgs/msg/String "{data: 'injected'}" --once
```

### The counter pair

```bash
ros2 run ros2_basics_py number_publisher
ros2 run ros2_basics_py number_counter
ros2 topic echo /number_count
```

Change what the publisher sends without editing code:

```bash
ros2 run ros2_basics_py number_publisher --ros-args -p number:=5 -p publish_frequency:=4.0
```

### Rewire it without editing code

Remapping changes which topic a node uses at launch time:

```bash
ros2 run ros2_basics_py talker --ros-args -r chatter:=/robot/chatter
ros2 run ros2_basics_py listener --ros-args -r chatter:=/robot/chatter
```

This is why you should never hard-code an absolute topic name.

---

## Common mistakes

**`ros2 topic echo` prints nothing.**
In order of likelihood: (1) nothing is publishing — check
`ros2 topic info /x --verbose` shows `Publisher count: 1`; (2) the names differ
by a namespace or a typo; (3) incompatible QoS ([lesson 10](10-qos.md)).

**The first few messages are missing.**
Normal. Discovery takes a moment, and a publisher created microseconds before
the first `publish()` has no subscribers yet. If the first message truly
matters, use a `TRANSIENT_LOCAL` (latched) profile.

**Setting the whole message at once.**
`msg = String('hello')` is not how it works. Create the message, then assign
its fields.

**The callback is slow and messages pile up.**
You are seeing queue depth in action. Fix the callback, or lower the rate.

**Two publishers on one topic.**
Perfectly legal — subscribers get both, interleaved. Usually a bug caused by
launching the same node twice.

---

## Exercise

[Exercise 02 — publisher and subscriber](../exercises/02-publisher-subscriber.md)

**Next:** [05 — Services](05-services.md)
