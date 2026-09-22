# 10 — Quality of Service (QoS)

**Goal:** understand the settings that decide whether two nodes connect at
all, and diagnose the "my topic is dead" bug.

**Code:** [`qos_publisher.py`](../src/ros2_basics_py/ros2_basics_py/qos_publisher.py),
[`qos_subscriber.py`](../src/ros2_basics_py/ros2_basics_py/qos_subscriber.py)

---

## The `10` you have been typing

Every time you wrote:

```python
self.create_publisher(String, 'chatter', 10)
```

that `10` was a shortcut. The full form is a **QoS profile**, and `10` means
*"keep the last 10 messages, reliable, volatile"*.

QoS is the set of promises the publisher makes and the subscriber requests. If
those promises are incompatible, **the middleware refuses to connect the two
nodes** — and it does so quietly. No exception, no crash, just a topic that
never delivers anything.

That is the failure this lesson exists to prevent.

---

## The four settings you actually need

### 1. Reliability

| Value | Meaning |
|---|---|
| `RELIABLE` | retry until delivered. Nothing is lost. Costs bandwidth and latency. |
| `BEST_EFFORT` | send once, no retries. Fast; drops under load. |

Use `RELIABLE` for commands and state. Use `BEST_EFFORT` for high-rate sensor
data where the next sample is already on its way — camera images, lidar scans.

### 2. Durability

| Value | Meaning |
|---|---|
| `VOLATILE` | a subscriber that joins late gets nothing that was sent before it. |
| `TRANSIENT_LOCAL` | the publisher stores the last N messages and sends them to late joiners. |

`TRANSIENT_LOCAL` is often called *latched*. It is how `/robot_description`,
`/map` and `/tf_static` work: publish once at start-up, and every node that
starts later still gets the value.

### 3. History and depth

| Value | Meaning |
|---|---|
| `KEEP_LAST` + `depth=N` | buffer the last N messages. This is what you want. |
| `KEEP_ALL` | buffer everything (up to middleware limits). Rarely useful. |

Depth is a queue. If your callback is slower than the publishing rate, the
queue fills and the oldest messages are dropped.

### 4. Deadline / liveliness / lifespan

You will meet these in industrial systems; you can ignore them for now.

---

## The compatibility rule

> **The publisher must offer at least as strong a guarantee as the subscriber
> requests.**

Which gives this table — worth memorising:

| Publisher | Subscriber | Connects? |
|---|---|---|
| `RELIABLE` | `BEST_EFFORT` | ✅ yes |
| `BEST_EFFORT` | `RELIABLE` | ❌ **no** |
| `TRANSIENT_LOCAL` | `VOLATILE` | ✅ yes |
| `VOLATILE` | `TRANSIENT_LOCAL` | ❌ **no** |

A publisher offering *more* than asked is fine. A publisher offering *less* is
a broken promise, so the connection is never made.

The `BEST_EFFORT` publisher + `RELIABLE` subscriber row is the single most
common cause of "my topic exists, `ros2 topic list` shows it, but nothing
arrives". It bites everyone at least once, usually with a camera driver.

---

## Writing a profile

```python
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

sensor_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5)

self.create_publisher(String, 'qos_demo', sensor_qos)
```

Pass the profile object exactly where you used to pass `10`.

ROS also ships ready-made profiles:

```python
from rclpy.qos import qos_profile_sensor_data, qos_profile_system_default

self.create_subscription(Image, 'camera/image_raw', self.cb, qos_profile_sensor_data)
```

`qos_profile_sensor_data` is `BEST_EFFORT` + small depth. If you subscribe to
a camera or lidar topic and get nothing, this is usually the fix.

### The three profiles in the demo

From [`qos_publisher.py`](../src/ros2_basics_py/ros2_basics_py/qos_publisher.py):

```python
PROFILES = {
    'default': QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10),
    'sensor': QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=5),
    'latched': QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1),
}
```

Both the publisher and the subscriber take a `profile` parameter and look the
profile up in this dictionary, so you can mix and match from the command line.

The subscriber imports the same dictionary, which is also a small lesson in
package layout:

```python
from ros2_basics_py.qos_publisher import PROFILES
```

Two nodes in the same package are just two modules; normal Python imports work.

---

## Try it — break it on purpose

This is the most useful experiment in the course. Run it twice.

**Compatible:**

```bash
# terminal 1
ros2 run ros2_basics_py qos_publisher  --ros-args -p profile:=sensor
# terminal 2
ros2 run ros2_basics_py qos_subscriber --ros-args -p profile:=sensor
```

Messages flow.

**Incompatible:**

```bash
# terminal 1
ros2 run ros2_basics_py qos_publisher  --ros-args -p profile:=sensor
# terminal 2
ros2 run ros2_basics_py qos_subscriber --ros-args -p profile:=default
```

Nothing arrives. The topic exists. Both nodes are alive and healthy. Humble
prints a warning about incompatible QoS, but it is easy to miss in a busy log.

**Now diagnose it the way you would in a real system:**

```bash
ros2 topic list                          # /qos_demo is there
ros2 topic info /qos_demo --verbose      # <- the answer is here
```

`--verbose` prints the QoS of every publisher and every subscriber separately.
Read down the Reliability and Durability lines and find the mismatch. Learn
this command; it turns a baffling silence into a ten-second fix.

**The latched profile:**

```bash
# terminal 1 — start it, wait ten seconds, leave it running
ros2 run ros2_basics_py qos_publisher --ros-args -p profile:=latched
# terminal 2 — start it late
ros2 run ros2_basics_py qos_subscriber --ros-args -p profile:=latched
```

The subscriber immediately receives the last message, even though it was sent
before the subscriber existed. Try the same with `profile:=default` on both
sides: the late joiner waits for the next message instead.

---

## Choosing a profile in practice

| Data | Profile |
|---|---|
| `/cmd_vel`, commands, state machines | default (reliable, depth 10) |
| camera, lidar, IMU at high rate | `qos_profile_sensor_data` (best effort) |
| `/map`, `/robot_description`, configuration published once | reliable + transient local, depth 1 |
| `/tf` | reliable, depth 100 (it is bursty) |
| `/tf_static` | transient local — handled for you by `StaticTransformBroadcaster` |

When in doubt, start with the default. Change it only when you have a reason,
and then check `ros2 topic info --verbose` on both sides.

---

## Common mistakes

**`ros2 topic echo` works but your node receives nothing.**
`ros2 topic echo` adapts its QoS automatically; your node does not. Compare
with `ros2 topic info /x --verbose`. This is the fingerprint of a QoS mismatch.

**Subscribing to a camera/lidar topic and getting silence.**
The driver publishes `BEST_EFFORT`. Use `qos_profile_sensor_data`.

**You set `depth=1` "to keep it simple".**
Now any callback slower than the publisher drops almost everything. Use 10
unless you have a reason.

**Latching does not work.**
`TRANSIENT_LOCAL` must be set on **both** sides, and the publisher must have
sent the message at least once.

**Changing QoS on a running node.**
Not possible — QoS is fixed when the publisher/subscription is created. You
would have to destroy and recreate it.

---

## Recap

- QoS is a contract. Incompatible contracts mean no connection, silently.
- The four settings that matter: reliability, durability, history, depth.
- The publisher must offer at least what the subscriber asks for.
- `ros2 topic info <topic> --verbose` shows both sides' QoS. It is the
  diagnostic tool for this whole class of bug.
- Sensors → `qos_profile_sensor_data`. Publish-once configuration →
  transient local. Everything else → the default.

## Exercise

[Exercise 08 — find the QoS bug](../exercises/08-qos.md)

**Next:** [11 — Executors and callback groups](11-executors-and-callback-groups.md)
