# Troubleshooting

The errors you will actually hit, in the order you will hit them.

Search this page for your error message.

---

## Setup and build

### `ros2: command not found`

ROS is not sourced in this terminal.

```bash
source /opt/ros/humble/setup.bash
```

Add it to `~/.bashrc` so every new terminal has it. Then open a new terminal —
editing `.bashrc` does not change terminals that are already open.

### `Package 'my_pkg' not found`

Either the package was never built, or the workspace is not sourced.

```bash
cd ~/ros2_ws
colcon build
source install/setup.bash        # in EVERY terminal that uses it
ros2 pkg list | grep my_pkg
```

> **The rule:** build, then source, in every terminal. Most "it does not work"
> reports in your first week are this.

### `No executable found`

The executable name comes from `setup.py`, not from the filename:

```python
    entry_points={
        'console_scripts': [
            'my_node = my_pkg.my_node:main',     # <- "my_node" is what ros2 run wants
        ],
    },
```

Add the entry, rebuild, re-source. Check with `ros2 pkg executables my_pkg`.

### `ModuleNotFoundError: No module named 'my_interfaces'`

You built the interfaces but did not re-source, or you only built the Python
package.

```bash
colcon build
source install/setup.bash
```

### `colcon build` fails with "Unknown type 'double'"

In `.msg`/`.srv` files the types are `float64`, `float32`, `int64`, `int32`,
`bool`, `string`. There is no `double`, `int` or `float`.

### A build worked, then started failing for no reason

Stale artefacts, usually after renaming or deleting something.

```bash
rm -rf build install log        # or ./scripts/clean.sh
colcon build
source install/setup.bash
```

### `SetuptoolsDeprecationWarning` spam during build

Harmless on Humble. Ignore it.

### Changes to a Python file do not take effect

You built without `--symlink-install`, so colcon copied the file. Either
rebuild every time, or build once with:

```bash
colcon build --symlink-install
```

Note that this does **not** apply to `setup.py` changes or new entry points —
those always need a rebuild.

---

## Nodes and topics

### `ros2 topic echo` prints nothing

In order of likelihood:

1. **Nothing is publishing.** `ros2 topic info /x --verbose` →
   `Publisher count: 0`.
2. **The names differ.** A typo, or a namespace you forgot.
   `ros2 topic list` shows the truth.
3. **QoS mismatch.** `ros2 topic info /x --verbose` and compare the
   Reliability/Durability lines of the publisher and the subscriber. See
   [lesson 10](10-qos.md).

### Your node receives nothing but `ros2 topic echo` works

Almost certainly QoS. `ros2 topic echo` adapts automatically; your node does
not. If the publisher is `BEST_EFFORT` and you asked for `RELIABLE`, you will
never connect.

```python
from rclpy.qos import qos_profile_sensor_data
self.create_subscription(Image, 'image', self.cb, qos_profile_sensor_data)
```

### The first few messages are missing

Normal. Discovery takes a moment, and a publisher created microseconds before
the first `publish()` has no subscribers yet. If the first message truly
matters, use a `TRANSIENT_LOCAL` (latched) profile.

### `msg = String('hello')` does not work

Create the message, then assign fields:

```python
msg = String()
msg.data = 'hello'
```

### `AssertionError: The 'x' field must be of type 'float'`

You assigned an `int` to a `float64` field. Write `2.0`, not `2`, or use
`float(value)`.

### The topic exists but has a slash-prefixed name you did not expect

You are in a namespace, or you hard-coded `'/topic'` instead of `'topic'`.
Relative names (no leading slash) are what you almost always want.

### Two publishers on the same topic

Legal — subscribers receive both, interleaved. Usually a bug from launching
the same node twice. Check `ros2 topic info /x --verbose`.

---

## Services and actions

### The service call hangs forever

1. `ros2 service list` — does the name exist? Check for a missing remap.
2. Are you blocking inside a callback?

```python
# WRONG inside any callback — deadlock
response = self._client.call(request)

# RIGHT
future = self._client.call_async(request)
future.add_done_callback(self.on_response)
```

See [lesson 11](11-executors-and-callback-groups.md).

### The client gets a malformed or empty response

The server's callback did not `return response`. Every service callback must
end with it.

### The whole node freezes when a service is called

`wait_for_service()` without a timeout, inside a callback. Use
`service_is_ready()` instead, and skip this cycle if it is not.

### An action client hangs after "goal accepted"

The server's `execute()` never called `succeed()`, `abort()` or `canceled()`,
or never returned a Result object.

### Cancelling an action does nothing

Two possible causes, and you usually need to fix both:

1. `execute()` never checks `goal_handle.is_cancel_requested`.
2. The node runs on a single-threaded executor, so the cancel request cannot
   be processed while `execute()` is running. Use `ReentrantCallbackGroup` +
   `MultiThreadedExecutor`.

### `AttributeError: 'CountUntil_FeedbackMessage' object has no attribute ...`

Feedback arrives wrapped: `feedback_msg.feedback.current_number`.

---

## Parameters

### `ParameterNotDeclaredException`

Call `self.declare_parameter('name', default)` in `__init__` before any
`get_parameter('name')`. Also check the spelling.

### `ros2 param set` says "Wrong parameter type"

The declared default fixed the type. A parameter declared with `1.0` is a
double and rejects `1`; one declared with `2` is an integer and rejects `2.5`.

### The YAML parameter file is ignored

The node name at the top of the file must match the node's **runtime** name
exactly, including any namespace:

```yaml
my_node:            # must equal what `ros2 node list` shows, minus the leading /
  ros__parameters:  # TWO underscores
    key: value
```

A mismatch is silent — no warning at all. Use `/**:` to match every node.

### `FileNotFoundError` for the YAML file at launch time

`setup.py` does not install the config folder:

```python
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
```

And use `get_package_share_directory('pkg')`, never an absolute path.

### `ros2 param set` succeeds but nothing changes

You read the value once in `__init__`. Add
`self.add_on_set_parameters_callback(...)` to react at runtime
([lesson 07](07-parameters.md)).

---

## Launch files

### `file 'x.launch.py' was not found`

It is not installed. Check `setup.py`:

```python
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
```

Then rebuild and re-source.

### `ros2 launch` runs but you see no output

Add `output='screen'` to the `Node(...)`.

### A node in the launch file never starts, with no error

You created the action but forgot to add it to `LaunchDescription([...])`.

### `InvalidParameterTypeException` when passing a launch argument

Launch arguments are strings. Convert them:

```python
ParameterValue(LaunchConfiguration('rate'), value_type=float)
```

### Nodes launch but do not talk to each other

A remap applied to one side only. Check with:

```bash
ros2 node info /node_a
ros2 node info /node_b
rqt_graph
```

### `TypeError` about `Node` in a launch file

You imported `rclpy.node.Node` instead of `launch_ros.actions.Node`.

---

## TF2

### `Could not find a connection between 'odom' and 'laser'`

A link is missing or a frame name has a typo.

```bash
ros2 run tf2_tools view_frames      # writes frames.pdf showing the real tree
```

### `Lookup would require extrapolation into the past`

The requested time is outside the buffer. Use `rclpy.time.Time()` for "latest
available", make sure broadcasters stamp with
`self.get_clock().now().to_msg()`, and check that `use_sim_time` is consistent
across all nodes.

### `TF_REPEATED_DATA` warnings, frames jittering

Two nodes publish the same child frame. Every frame has exactly one parent and
one publisher.

### Transforms silently ignored / `TF_NAN_INPUT`

An all-zero quaternion. Identity is `(x=0, y=0, z=0, w=1)`.

### Everything is mirrored or rotated wrongly

`header.frame_id` is the **parent**, `child_frame_id` is the **child**. Or you
swapped the arguments to `lookup_transform(target, source, time)`.

---

## Executors and freezing

### The node stops responding for a while, then recovers

Something blocks inside a callback — `time.sleep()`, a blocking service call,
a long computation, a `while` loop. One thread runs all callbacks by default.

Fix: `call_async`, or a `MultiThreadedExecutor` **plus** a
`ReentrantCallbackGroup` ([lesson 11](11-executors-and-callback-groups.md)).

### "I switched to MultiThreadedExecutor and nothing changed"

Your callbacks are still in the node's default mutually-exclusive group. You
must also pass `callback_group=ReentrantCallbackGroup()`.

### A timer or subscription stops working after a while

You did not keep a reference to it. `self._timer = self.create_timer(...)`,
not `self.create_timer(...)` — otherwise it can be garbage collected.

---

## Networking

### Nodes on two machines cannot see each other

Check, in order:

1. the same `ROS_DOMAIN_ID` on both (`printenv | grep ROS_DOMAIN`),
2. `ROS_LOCALHOST_ONLY` is not set to 1,
3. the same `RMW_IMPLEMENTATION`,
4. the firewall allows UDP multicast,
5. `ros2 doctor --report` on both machines and compare.

### You see a colleague's nodes in `ros2 node list`

You share a domain. Pick your own:

```bash
export ROS_DOMAIN_ID=42
```

### Discovery is slow or flaky in a container

Run the container with `--net=host` (as `docker/run.sh` does), or set
`ROS_LOCALHOST_ONLY=1` if everything is in one container.

---

## Testing

### `RuntimeError` about the context being already initialized

`rclpy.init()` was called twice, or a previous test never called `shutdown()`.
Use a pytest fixture that does both.

### A test hangs forever

Something called `rclpy.spin()` or waited on a future without a timeout. Use
`executor.spin_once(timeout_sec=0.05)` in a bounded loop.

### `colcon test` passes but the tests are broken

`colcon test` exits 0 on failures unless you ask otherwise:

```bash
colcon test --return-code-on-test-failure
colcon test-result --all --verbose
```

---

## Still stuck

Gather this before asking anyone:

```bash
ros2 doctor --report
ros2 node list
ros2 topic list -t
ros2 topic info /the_topic --verbose
```

Plus the full error text and what you expected instead. Ninety percent of the
time, writing that message finds the bug for you.

---

Back to [the course index](README.md) ·
[cheat sheet](cheatsheet.md) · [glossary](glossary.md)
