# Exercise 08 — Find the QoS bug

**After:** [lesson 10 — QoS](../docs/10-qos.md)

---

This one is different. You write almost no code — you **debug**.

## The scenario

A colleague hands you two nodes. The publisher runs. The subscriber runs.
`ros2 topic list` shows the topic. Neither node prints an error.

The subscriber receives **nothing**.

Create these two files exactly as given, build, and reproduce it.

`my_exercises/my_exercises/imu_publisher.py`:

```python
#!/usr/bin/env python3
"""Exercise 08 - a 'sensor driver' publishing at high rate."""

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class ImuPublisher(Node):
    def __init__(self):
        super().__init__('imu_publisher')

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5)

        self._publisher = self.create_publisher(String, 'imu_data', qos)
        self._count = 0
        self._timer = self.create_timer(0.05, self.publish_reading)

        self.get_logger().info('publishing /imu_data at 20 Hz')

    def publish_reading(self):
        msg = String()
        msg.data = 'reading %d' % self._count
        self._publisher.publish(msg)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = ImuPublisher()
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

`my_exercises/my_exercises/imu_monitor.py`:

```python
#!/usr/bin/env python3
"""Exercise 08 - the node that mysteriously receives nothing."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ImuMonitor(Node):
    def __init__(self):
        super().__init__('imu_monitor')

        # The "just use 10" default.
        self._subscription = self.create_subscription(
            String, 'imu_data', self.on_reading, 10)

        self.get_logger().info('listening on /imu_data')

    def on_reading(self, msg):
        self.get_logger().info('got %s' % msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = ImuMonitor()
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

---

## The task

1. **Reproduce it.** Run both. Confirm the monitor prints nothing.
2. **Confirm data is really being published.** Prove it without touching the
   code.
3. **Diagnose it with one command.** Find the exact incompatible setting.
4. **Fix the subscriber** — two different ways.
5. **Explain** why `ros2 topic echo` behaves differently from your node.

Write your answers down before reading the solution.

---

## Hints

<details>
<summary>Hint 1 — is anything being sent?</summary>

```bash
ros2 topic echo /imu_data
ros2 topic hz /imu_data
```

</details>

<details>
<summary>Hint 2 — the one command that shows the answer</summary>

`ros2 topic info /imu_data` is not enough. Add `--verbose`.

</details>

<details>
<summary>Hint 3 — the rule</summary>

The publisher must offer **at least** as strong a guarantee as the subscriber
requests.

</details>

---

## Solution

### 1. Reproduce

```bash
# terminal 1
ros2 run my_exercises imu_publisher
# terminal 2
ros2 run my_exercises imu_monitor
```

The publisher logs `publishing /imu_data at 20 Hz`. The monitor logs
`listening on /imu_data` and then stays silent forever.

### 2. Is data flowing?

```bash
ros2 topic echo /imu_data
```

Readings scroll past. So the publisher is fine, and the topic name is fine.
The problem is specific to the connection between these two nodes.

### 3. Diagnose

```bash
ros2 topic info /imu_data --verbose
```

```
Type: std_msgs/msg/String

Publisher count: 1

Node name: imu_publisher
...
QoS profile:
  Reliability: BEST_EFFORT          <-- the publisher only promises best effort
  Durability: VOLATILE
  History (Depth): KEEP_LAST (5)

Subscription count: 1

Node name: imu_monitor
...
QoS profile:
  Reliability: RELIABLE             <-- the subscriber demands reliable
  Durability: VOLATILE
  History (Depth): KEEP_LAST (10)
```

There it is. The subscriber **requests** `RELIABLE`; the publisher only
**offers** `BEST_EFFORT`. That is a broken promise, so the middleware never
connects them.

Note `Publisher count: 1` and `Subscription count: 1` — both endpoints exist.
Counting endpoints is not enough; you have to read the QoS.

### 4. Two fixes

**Fix A — the ready-made sensor profile.** Best when the data really is sensor
data:

```python
from rclpy.qos import qos_profile_sensor_data

self._subscription = self.create_subscription(
    String, 'imu_data', self.on_reading, qos_profile_sensor_data)
```

**Fix B — an explicit profile.** Best when you want the settings visible:

```python
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,   # match the publisher
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10)

self._subscription = self.create_subscription(
    String, 'imu_data', self.on_reading, qos)
```

Either way, re-run `ros2 topic info /imu_data --verbose` and confirm both
sides now say `BEST_EFFORT`.

**What about fixing the publisher instead?** Changing it to `RELIABLE` also
works and is compatible with both kinds of subscriber. But for a 20 Hz (or
200 Hz) sensor it is the wrong call: reliable delivery means retransmitting
stale readings you no longer care about, costing bandwidth and latency. For
sensor streams, best effort on the publisher is correct — the subscriber is
what should adapt.

### 5. Why `ros2 topic echo` worked

`ros2 topic echo` inspects the existing publishers and **adapts its own QoS**
to match them. Your node does not; it asks for what you wrote and accepts
nothing less.

This is why "`echo` works but my node gets nothing" is the fingerprint of a
QoS mismatch. It is one of the most useful diagnostic signals in ROS 2 —
remember it.

---

## The reverse case

Try it the other way round, to see the asymmetry:

- publisher `RELIABLE`, subscriber `BEST_EFFORT` → **connects fine**. The
  publisher offers more than asked for, which is allowed.

And for durability:

- publisher `TRANSIENT_LOCAL`, subscriber `VOLATILE` → connects.
- publisher `VOLATILE`, subscriber `TRANSIENT_LOCAL` → does **not** connect.

Same rule every time: **offered ≥ requested**.

---

## Going further

- Add `TRANSIENT_LOCAL` to the publisher, restart only the subscriber, and
  watch it immediately receive the last message that was sent before it
  started. That is how `/map` and `/robot_description` work.
- Set the subscriber's `depth` to 1 and add `time.sleep(0.5)` to
  `on_reading`. The publisher sends 20 messages a second; watch how many the
  subscriber actually processes, and where the rest go.
- Subscribe to a real sensor topic in a simulator or on a real driver. If you
  get nothing, you now know the first command to run.

---

**Done with the exercises.** Back to [the index](README.md), or finish the
course with the [capstone](../docs/16-capstone-catch-them-all.md).
