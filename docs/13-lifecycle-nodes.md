# 13 — Lifecycle nodes

**Goal:** write a node that waits to be told when to start, instead of doing
its job the moment it launches.

**Code:** [`lifecycle_number_publisher.py`](../src/ros2_basics_py/ros2_basics_py/lifecycle_number_publisher.py)

---

## Why

Every node you have written so far starts working immediately. `__init__`
creates the publisher, the timer fires, data flows.

That is fine for a demo. It is a problem when:

- a camera driver grabs the USB device before you know which camera you want,
- ten nodes all start publishing while the robot is still being configured,
- you need to restart one node's hardware without killing the process,
- you want to bring a system up in a defined order.

A **lifecycle node** (also called a *managed node*) has a state machine that
someone else drives. It allocates resources when told to configure, and starts
producing output only when told to activate.

---

## The state machine

```
    unconfigured ──configure──> inactive ──activate──> active
         ^                        │  ^                    │
         └────────cleanup─────────┘  └────deactivate──────┘
```

| State | What it means |
|---|---|
| **unconfigured** | the process is running, nothing is allocated |
| **inactive** | everything is allocated, but no data goes out |
| **active** | doing the job |
| **finalized** | shutting down |

The transitions you handle in code: `on_configure`, `on_activate`,
`on_deactivate`, `on_cleanup`, `on_shutdown` (and `on_error`).

The rule of thumb:

- **`on_configure`** — acquire things. Open the serial port, read parameters,
  create publishers, subscriptions and timers.
- **`on_activate`** — start emitting. Usually just `return super().on_activate(state)`.
- **`on_deactivate`** — stop emitting, keep everything allocated.
- **`on_cleanup`** — release everything `on_configure` acquired.

---

## The code

Full file —
[`lifecycle_number_publisher.py`](../src/ros2_basics_py/ros2_basics_py/lifecycle_number_publisher.py):

```python
from example_interfaces.msg import Int64
import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn


class LifecycleNumberPublisher(Node):
    """Publishes an incrementing number, but only while it is active."""

    def __init__(self):
        super().__init__('lifecycle_number_publisher')
        self._publisher = None
        self._timer = None
        self._counter = 0
        self.get_logger().info('constructed, currently unconfigured')

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Allocate resources. Still not publishing anything."""
        self.get_logger().info('on_configure: creating publisher and timer')
        self._publisher = self.create_lifecycle_publisher(Int64, 'lifecycle_number', 10)
        self._timer = self.create_timer(1.0, self.publish_number)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start doing the real work."""
        self.get_logger().info('on_activate: now publishing')
        # The base class flips the publisher into its active state.
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop publishing but keep everything allocated."""
        self.get_logger().info('on_deactivate: pausing')
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Release everything acquired in on_configure."""
        self.get_logger().info('on_cleanup: destroying publisher and timer')
        self.destroy_timer(self._timer)
        self.destroy_lifecycle_publisher(self._publisher)
        self._timer = None
        self._publisher = None
        self._counter = 0
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('on_shutdown')
        return TransitionCallbackReturn.SUCCESS

    def publish_number(self):
        self._counter += 1
        msg = Int64()
        msg.data = self._counter
        # While the node is inactive this publish is a no-op.
        self._publisher.publish(msg)
```

### The five things that differ from a normal node

1. **`from rclpy.lifecycle import Node`** — a different base class from
   `rclpy.node.Node`. Same methods, plus the state machine.

2. **`__init__` allocates nothing.** It sets the attributes to `None` and
   returns. All real setup happens in `on_configure`. This is the whole point.

3. **`create_lifecycle_publisher(...)`** instead of `create_publisher(...)`.
   A lifecycle publisher knows about the state machine: while the node is
   inactive, `publish()` is a **silent no-op**. Nothing leaks out before the
   node is meant to be running — so `publish_number` needs no `if active:`
   guard.

4. **Every transition callback returns a `TransitionCallbackReturn`**:
   - `SUCCESS` → the transition completes,
   - `FAILURE` → the node stays in the previous state (use this when the
     hardware is not there),
   - `ERROR` → jumps to the error-processing state.

5. **`on_activate` and `on_deactivate` call `super()`.** The base class is
   what actually flips the lifecycle publishers. Override without calling
   `super()` and your publisher never activates — a very confusing bug.

Note that the timer keeps firing while the node is inactive; it is the
*publish* that is suppressed. If the callback did something expensive, you
would want to cancel the timer in `on_deactivate` yourself.

---

## Try it

```bash
# terminal 1
ros2 run ros2_basics_py lifecycle_number_publisher
```

Nothing happens. That is correct — it is unconfigured.

```bash
# terminal 2
ros2 lifecycle nodes
ros2 lifecycle get /lifecycle_number_publisher
# -> unconfigured [1]
```

Now drive it through the state machine, watching terminal 1 at each step:

```bash
ros2 lifecycle set /lifecycle_number_publisher configure
ros2 lifecycle get /lifecycle_number_publisher      # -> inactive [2]
```

The publisher exists now. Check that it is quiet:

```bash
ros2 topic list                        # /lifecycle_number is there
ros2 topic echo /lifecycle_number      # ... but nothing arrives
```

Leave that echo running and activate:

```bash
ros2 lifecycle set /lifecycle_number_publisher activate
```

Numbers start flowing. Then:

```bash
ros2 lifecycle set /lifecycle_number_publisher deactivate   # stops, keeps state
ros2 lifecycle set /lifecycle_number_publisher activate     # resumes counting
ros2 lifecycle set /lifecycle_number_publisher deactivate
ros2 lifecycle set /lifecycle_number_publisher cleanup      # back to unconfigured
```

Notice that `deactivate` → `activate` keeps counting where it stopped, while
`cleanup` resets the counter to zero — because `on_cleanup` sets it back.

See every transition available from the current state:

```bash
ros2 lifecycle list /lifecycle_number_publisher
```

---

## Launching them in order

Nodes do not usually get configured by hand. In a real system a *lifecycle
manager* does it — `nav2_lifecycle_manager` is the well-known one. From a
launch file you can also drive transitions with
`launch_ros.actions.LifecycleNode` plus `EmitEvent`, or simply run a small
manager node of your own that calls the `change_state` service on each node in
the right order.

For learning purposes, the CLI above is enough.

---

## Common mistakes

**The node publishes nothing even after activate.**
You overrode `on_activate` without calling `return super().on_activate(state)`.

**`AttributeError: 'NoneType' object has no attribute 'publish'`**
A callback ran before `on_configure`, or after `on_cleanup`. Guard with
`if self._publisher is None: return`, or cancel the timer in `on_cleanup`
(which this example does).

**`ros2 lifecycle nodes` shows nothing.**
You inherited from `rclpy.node.Node` instead of `rclpy.lifecycle.Node`.

**`Transition is not registered` / `Unknown transition`.**
You cannot go straight from unconfigured to active. Configure first.
`ros2 lifecycle list <node>` shows what is legal right now.

**You put the hardware setup in `__init__`.**
Then the node is not really managed. Move it into `on_configure`.

**Every node in the project is a lifecycle node.**
Overkill. Use them for drivers and anything whose start-up order matters;
plain nodes are fine for everything else.

---

## Recap

- A lifecycle node starts idle and waits to be told what to do.
- States: unconfigured → inactive → active, and back.
- `on_configure` acquires, `on_activate` starts output, `on_deactivate` stops
  it, `on_cleanup` releases.
- Inherit `rclpy.lifecycle.Node`, use `create_lifecycle_publisher`, return
  `TransitionCallbackReturn.SUCCESS`, and call `super()` in activate and
  deactivate.
- Drive it with `ros2 lifecycle get|set|list`.

**Next:** [14 — Testing](14-testing.md)
