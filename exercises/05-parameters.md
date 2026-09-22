# Exercise 05 — Parameters

**After:** [lesson 07 — Parameters](../docs/07-parameters.md)

---

## The task

Take the counter publisher from [exercise 02](02-publisher-subscriber.md) and
make every part of its behaviour configurable — without restarting it.

### Requirements

Node `configurable_counter`, publishing `Int64` on `counter`:

1. Parameters, all with a **description**:
   - `start_value` (int, default `0`)
   - `step` (int, default `1`)
   - `publish_frequency` (double, default `1.0`), **limited to 0.1 – 20.0 Hz**
   - `enabled` (bool, default `true`)
2. Changing `publish_frequency` at runtime must change the actual rate.
3. Changing `enabled` to `false` must stop publishing — without killing the
   node — and `true` must resume.
4. `step` must be rejected if it is `0`, with a reason the CLI prints.
5. A YAML file that sets all four, loadable with `--params-file`.

### Check yourself

```bash
ros2 run my_exercises configurable_counter
```

```bash
ros2 param list
ros2 param describe /configurable_counter publish_frequency
ros2 param set /configurable_counter publish_frequency 5.0     # accepted
ros2 param set /configurable_counter publish_frequency 50.0    # rejected (range)
ros2 param set /configurable_counter step 0                    # rejected (callback)
ros2 param set /configurable_counter enabled false             # goes quiet
ros2 topic hz /counter                                         # confirm the rate
```

---

## Hints

<details>
<summary>Hint 1 — declaring with a description and a range</summary>

```python
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor

self.declare_parameter(
    'publish_frequency', 1.0,
    ParameterDescriptor(
        description='...',
        floating_point_range=[FloatingPointRange(from_value=0.1, to_value=20.0, step=0.0)]))
```

</details>

<details>
<summary>Hint 2 — reacting to changes</summary>

```python
self.add_on_set_parameters_callback(self.on_parameter_change)

def on_parameter_change(self, params):
    for param in params:
        ...
    return SetParametersResult(successful=True)
```

`params` is a **list** — one `ros2 param set` can change several at once.

</details>

<details>
<summary>Hint 3 — changing a timer's rate</summary>

A timer's period cannot be edited. Cancel it and create a new one:

```python
self._timer.cancel()
self._timer = self.create_timer(1.0 / new_frequency, self.publish_count)
```

</details>

<details>
<summary>Hint 4 — rejecting a value</summary>

```python
return SetParametersResult(successful=False, reason='step must not be zero')
```

The CLI prints your reason.

</details>

---

## Solution

`my_exercises/my_exercises/configurable_counter.py`:

```python
#!/usr/bin/env python3
"""Exercise 05 - a node you can retune completely at runtime."""

from example_interfaces.msg import Int64
from rcl_interfaces.msg import (FloatingPointRange, ParameterDescriptor,
                                SetParametersResult)
import rclpy
from rclpy.node import Node


class ConfigurableCounter(Node):
    """Publishes a counter whose every aspect is a parameter."""

    def __init__(self):
        super().__init__('configurable_counter')

        self.declare_parameter(
            'start_value', 0,
            ParameterDescriptor(description='Value the counter starts from.'))

        self.declare_parameter(
            'step', 1,
            ParameterDescriptor(description='Added to the counter each tick.'))

        self.declare_parameter(
            'publish_frequency', 1.0,
            ParameterDescriptor(
                description='How often to publish, in Hz.',
                floating_point_range=[
                    FloatingPointRange(from_value=0.1, to_value=20.0, step=0.0)
                ]))

        self.declare_parameter(
            'enabled', True,
            ParameterDescriptor(description='Set false to pause publishing.'))

        self._count = self.get_parameter('start_value').value
        self._step = self.get_parameter('step').value
        self._enabled = self.get_parameter('enabled').value
        frequency = self.get_parameter('publish_frequency').value

        self._publisher = self.create_publisher(Int64, 'counter', 10)
        self._timer = self.create_timer(1.0 / frequency, self.publish_count)

        # Called BEFORE each new value is committed. Return successful=False
        # to veto the change.
        self.add_on_set_parameters_callback(self.on_parameter_change)

        self.get_logger().info(
            'counting from %d in steps of %d at %.2f Hz'
            % (self._count, self._step, frequency))

    def publish_count(self):
        if not self._enabled:
            return

        msg = Int64()
        msg.data = self._count
        self._publisher.publish(msg)

        self._count += self._step

    def on_parameter_change(self, params):
        for param in params:
            if param.name == 'step':
                if param.value == 0:
                    return SetParametersResult(
                        successful=False, reason='step must not be zero')
                self._step = param.value
                self.get_logger().info('step is now %d' % param.value)

            elif param.name == 'enabled':
                self._enabled = param.value
                self.get_logger().info(
                    'publishing %s' % ('resumed' if param.value else 'paused'))

            elif param.name == 'publish_frequency':
                # The declared range already blocks 0.1 > f > 20.0, so all we
                # do here is re-arm the timer with the new period.
                self._timer.cancel()
                self._timer = self.create_timer(1.0 / param.value, self.publish_count)
                self.get_logger().info('frequency is now %.2f Hz' % param.value)

            elif param.name == 'start_value':
                # Only meaningful at startup; say so instead of ignoring it.
                self.get_logger().warn(
                    'start_value only takes effect when the node starts')

        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = ConfigurableCounter()
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

`my_exercises/config/counter.yaml`:

```yaml
# The top-level key MUST match the node's runtime name exactly.
configurable_counter:
  ros__parameters:
    start_value: 100
    step: 5
    publish_frequency: 4.0
    enabled: true
```

Install it in `setup.py`:

```python
import os
from glob import glob

    data_files=[
        ...
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
```

Run it:

```bash
ros2 run my_exercises configurable_counter --ros-args \
    --params-file src/my_exercises/config/counter.yaml
```

---

## Why it is written this way

**The range is declared, not checked in code.** `floating_point_range` is
enforced by the middleware itself — your callback is never even reached for an
out-of-range value, and `ros2 param describe` documents the limit for free.

**The lower bound is not cosmetic.** The timer period is `1.0 / frequency`.
Without a minimum, `0.0` would be a division by zero that kills the node.

**`step == 0` is rejected in the callback.** A range cannot express "anything
but zero", so this is the kind of rule the callback exists for. Returning a
`reason` means the person at the terminal sees why.

**`enabled` guards the publish, not the timer.** Simpler, and resuming is
instant. If the callback did expensive work you would cancel the timer
instead.

**`start_value` warns instead of silently doing nothing.** A parameter that
only applies at start-up is fine — quietly ignoring an attempt to change it is
not. Say so.

**Every parameter has a description.** One line each, and `ros2 param
describe` becomes real documentation for whoever runs your node next.

---

## Going further

- Add `ros2 param dump /configurable_counter > tuned.yaml`, then restart the
  node with `--params-file tuned.yaml`. That is the real tuning workflow.
- Run two copies in different namespaces (`--ros-args -r __ns:=/a`) and set
  different frequencies on each. Parameters are per node.
- Move the YAML load into a launch file ([exercise 06](06-launch-file.md)).

**Next:** [Exercise 06 — a launch file](06-launch-file.md)
