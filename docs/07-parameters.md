# 07 — Parameters

**Goal:** make a node configurable without editing its code, and make it react
to changes while it runs.

**Code:** [`parameter_demo.py`](../src/ros2_basics_py/ros2_basics_py/parameter_demo.py),
[`number_publisher.py`](../src/ros2_basics_py/ros2_basics_py/number_publisher.py),
[`config/parameter_demo.yaml`](../src/ros2_basics_py/config/parameter_demo.yaml)

---

## The idea

A parameter is a named setting that belongs to **one node**, set from outside
the code: on the command line, in a launch file, or from a YAML file.

Anything you are tempted to hard-code is a parameter candidate: a serial port,
a topic rate, a PID gain, a robot name, a frame id.

```
                 ros2 param set /number_publisher number 7
                                  │
                                  ▼
          ┌──────────────────────────────────────┐
          │  node /number_publisher              │
          │    number             = 7            │
          │    publish_frequency  = 1.0          │
          └──────────────────────────────────────┘
```

Parameters are **per node**, not global. Two nodes can both have a `rate`
parameter with different values and never collide.

---

## Declare, then get

The minimal version, from
[`number_publisher.py`](../src/ros2_basics_py/ros2_basics_py/number_publisher.py):

```python
        # Declare before you get. An undeclared parameter raises
        # ParameterNotDeclaredException, which is the behaviour you want:
        # typos fail loudly instead of silently returning a default.
        self.declare_parameter('number', 2)
        self.declare_parameter('publish_frequency', 1.0)

        self._number = self.get_parameter('number').value
        frequency = self.get_parameter('publish_frequency').value
```

Three things to notice:

1. **`declare_parameter(name, default)`** must come first. It tells ROS the
   parameter exists and — from the default value — what type it is.
2. **The default value sets the type.** `2` makes it an integer, so
   `-p number:=2.5` will be rejected. `1.0` makes it a double, so
   `-p publish_frequency:=1` is *also* rejected (an integer is not a double).
   Write `1.0`, not `1`, whenever you mean a float.
3. **`.value`** unwraps the result. `get_parameter('number')` returns a
   `Parameter` object; `.value` is the plain Python value. Forgetting `.value`
   gives you strange errors like `unsupported operand type(s)`.

Run it with different values without touching the file:

```bash
ros2 run ros2_basics_py number_publisher
ros2 run ros2_basics_py number_publisher --ros-args -p number:=7 -p publish_frequency:=5.0
```

`--ros-args` marks the start of ROS-specific arguments. Everything after it is
consumed by ROS, not by your `sys.argv`.

---

## The production version

Reading a value at startup is the 80% case. A parameter you would ship has
three more things: a **description**, a **valid range**, and a **callback** so
the node reacts without a restart.

Here is the full file —
[`parameter_demo.py`](../src/ros2_basics_py/ros2_basics_py/parameter_demo.py):

```python
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
import rclpy
from rclpy.node import Node


class ParameterDemo(Node):
    """A node whose behaviour can be retuned at runtime."""

    def __init__(self):
        super().__init__('parameter_demo')

        self.declare_parameter(
            'robot_name',
            'rosbot',
            ParameterDescriptor(description='Name used in the log lines.'))

        self.declare_parameter(
            'publish_frequency',
            1.0,
            ParameterDescriptor(
                description='How often the node logs, in Hz.',
                floating_point_range=[
                    FloatingPointRange(from_value=0.1, to_value=10.0, step=0.0)
                ]))

        self.declare_parameter(
            'enabled',
            True,
            ParameterDescriptor(description='Set false to mute the node.'))

        self._robot_name = self.get_parameter('robot_name').value
        self._enabled = self.get_parameter('enabled').value
        frequency = self.get_parameter('publish_frequency').value

        self._timer = self.create_timer(1.0 / frequency, self.on_timer)

        # Runs before a new value is committed. Return success=False to veto.
        self.add_on_set_parameters_callback(self.on_parameter_change)

        self.get_logger().info('parameter_demo started as "%s"' % self._robot_name)

    def on_timer(self):
        if self._enabled:
            self.get_logger().info('%s is alive' % self._robot_name)

    def on_parameter_change(self, params):
        for param in params:
            if param.name == 'robot_name':
                if not param.value:
                    return SetParametersResult(
                        successful=False, reason='robot_name must not be empty')
                self._robot_name = param.value

            elif param.name == 'enabled':
                self._enabled = param.value

            elif param.name == 'publish_frequency':
                # The declared range already blocks values outside 0.1 - 10.0,
                # so here we only need to re-arm the timer.
                self._timer.cancel()
                self._timer = self.create_timer(1.0 / param.value, self.on_timer)
                self.get_logger().info('frequency is now %.2f Hz' % param.value)

        return SetParametersResult(successful=True)
```

### The descriptor

```python
ParameterDescriptor(description='Name used in the log lines.')
```

This is what `ros2 param describe` prints. It costs one line and it is the
difference between a parameter someone else can use and one they have to read
your source to understand.

### The range

```python
floating_point_range=[FloatingPointRange(from_value=0.1, to_value=10.0, step=0.0)]
```

The middleware itself now refuses values outside 0.1–10.0 — your callback is
never even called. `step=0.0` means "any value in the range" (use e.g. `0.5`
if you want discrete steps). For integers the equivalent is `IntegerRange`.

Why the lower bound matters here: the timer period is `1.0 / frequency`, so a
frequency of `0.0` would be a division by zero. The range makes that
impossible instead of merely unlikely.

### The set-callback

```python
self.add_on_set_parameters_callback(self.on_parameter_change)
```

- It runs **before** the new value is stored, once per `ros2 param set`.
- `params` is a **list** of `Parameter` objects — one `set` call can change
  several at once, so always loop.
- Returning `SetParametersResult(successful=False, reason='...')` **vetoes**
  the change. The CLI prints your reason. This is how you validate anything a
  range cannot express.
- Returning `successful=True` accepts it. If the node needs to *do* something
  about the new value — re-arm a timer, reopen a port — do it here.

The timer re-arm pattern is worth memorising:

```python
self._timer.cancel()
self._timer = self.create_timer(new_period, self.on_timer)
```

A timer's period cannot be changed in place; you cancel the old one and make a
new one.

---

## Parameters from a YAML file

Once there is more than a handful, put them in a file.
[`config/parameter_demo.yaml`](../src/ros2_basics_py/config/parameter_demo.yaml):

```yaml
parameter_demo:
  ros__parameters:
    robot_name: "humble_bot"
    publish_frequency: 2.0
    enabled: true

# Applies to every node that loads this file.
/**:
  ros__parameters:
    use_sim_time: false
```

The structure is rigid and has exactly two levels above your values:

```
<node_name>:
  ros__parameters:
    <key>: <value>
```

- `<node_name>` must match the node's **actual runtime name**, including any
  namespace (`/my_robot/parameter_demo:`). If it does not match, the whole
  block is **silently ignored** — no error, no warning. This is the number one
  reason a YAML file "does not work".
- `ros__parameters` has **two** underscores. One underscore is silently
  ignored too.
- `/**` matches every node, which is how `use_sim_time` is usually set.

Load it directly:

```bash
ros2 run ros2_basics_py parameter_demo --ros-args \
    --params-file src/ros2_basics_py/config/parameter_demo.yaml
```

Or from a launch file ([lesson 08](08-launch-files.md)) —
[`params_demo.launch.py`](../src/ros2_basics_py/launch/params_demo.launch.py):

```python
    config = os.path.join(
        get_package_share_directory('ros2_basics_py'),
        'config',
        'parameter_demo.yaml')

    parameter_demo = Node(
        package='ros2_basics_py',
        executable='parameter_demo',
        name='parameter_demo',
        output='screen',
        parameters=[config],
    )
```

`get_package_share_directory` finds the *installed* copy of the file. Never
hard-code an absolute path — it will break on every other machine.

For the YAML file to be installed at all, `setup.py` must copy it:

```python
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
```

Forget that line and you get `FileNotFoundError` at launch time.

---

## Try it

```bash
# terminal 1
ros2 run ros2_basics_py parameter_demo
```

```bash
# terminal 2 — look around
ros2 param list
ros2 param describe /parameter_demo publish_frequency
ros2 param get /parameter_demo robot_name
```

Now change things while it runs, and watch terminal 1 react:

```bash
ros2 param set /parameter_demo robot_name "humble_bot"    # accepted
ros2 param set /parameter_demo publish_frequency 5.0      # accepted, speeds up
ros2 param set /parameter_demo enabled false              # goes quiet
ros2 param set /parameter_demo enabled true               # back
```

Now try to break it. Both of these are refused, for different reasons:

```bash
ros2 param set /parameter_demo publish_frequency 500.0    # outside the range
ros2 param set /parameter_demo robot_name ""              # vetoed by the callback
```

Save the current configuration to a file you can reload later:

```bash
ros2 param dump /parameter_demo
```

---

## Common mistakes

**`ParameterNotDeclaredException`**
You called `get_parameter` for something you never declared, or you misspelled
the name. Declare it in `__init__`.

**`ros2 param set` says "Wrong parameter type".**
The declared default set the type. `1.0` is a double and will not accept `1`;
`2` is an integer and will not accept `2.5`. Fix the default or the value.

**The YAML file has no effect.**
Check the node name at the top of the file against `ros2 node list` output,
including the namespace. Check `ros__parameters` has two underscores.

**`ros2 param set` succeeds but nothing changes.**
You read the value once in `__init__` and cached it. That is fine for
start-up-only settings, but if you want live updates you need the
`add_on_set_parameters_callback` shown above.

**Dividing by a parameter without a range.**
`1.0 / frequency` with `frequency = 0.0` crashes the node. Declare a range.

**Hard-coding the path to the YAML file.**
Use `get_package_share_directory`, and make sure `setup.py` installs the file.

---

## Recap

- `declare_parameter(name, default)` first, then `get_parameter(name).value`.
- The default value fixes the type. Write `1.0` for floats.
- `--ros-args -p name:=value` on the CLI, `parameters=[...]` in launch,
  `--params-file` or `parameters=[path]` for YAML.
- Add a `ParameterDescriptor` so `ros2 param describe` is useful, and a range
  so bad values are impossible.
- `add_on_set_parameters_callback` lets the node react at runtime; return
  `SetParametersResult(successful=False, reason=...)` to reject a value.

## Exercise

[Exercise 05 — make a node configurable](../exercises/05-parameters.md)

**Next:** [08 — Launch files](08-launch-files.md)
