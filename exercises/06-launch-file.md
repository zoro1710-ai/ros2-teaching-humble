# Exercise 06 — A launch file

**After:** [lesson 08 — Launch files](../docs/08-launch-files.md)

---

## The task

Start the whole exercise application with one command, and make it
configurable without editing code.

### Requirements

A launch file `counter_app.launch.py` that starts:

1. `configurable_counter` (from [exercise 05](05-parameters.md)), named
   `fast_counter`, publishing on `/fast/counter`.
2. A second `configurable_counter`, named `slow_counter`, publishing on
   `/slow/counter` — **the same executable, twice**.
3. `counter_subscriber` (from [exercise 02](02-publisher-subscriber.md)),
   listening to `/fast/counter`.

Plus:

4. A launch argument `fast_rate` (default `5.0`) that sets the fast counter's
   `publish_frequency`.
5. The slow counter loads its parameters from a **YAML file** in the package.
6. All three nodes print to the terminal.

### Check yourself

```bash
ros2 launch my_exercises counter_app.launch.py
ros2 launch my_exercises counter_app.launch.py fast_rate:=10.0
ros2 launch my_exercises counter_app.launch.py --show-args
```

```bash
ros2 node list          # /fast_counter, /slow_counter, /counter_subscriber
ros2 topic list         # /fast/counter and /slow/counter
ros2 topic hz /fast/counter
rqt_graph               # the subscriber must be wired to /fast/counter only
```

---

## Hints

<details>
<summary>Hint 1 — running one executable twice</summary>

Give each `Node(...)` a different `name=`. The name in the launch file
overrides the one in `super().__init__()`.

</details>

<details>
<summary>Hint 2 — the topic names</summary>

The node publishes on the relative name `counter`. Remap it:

```python
remappings=[('counter', 'fast/counter')],
```

No leading slash on the left side.

</details>

<details>
<summary>Hint 3 — the launch argument type</summary>

Launch arguments are **strings**. `publish_frequency` was declared as a
double, so it needs converting:

```python
ParameterValue(LaunchConfiguration('fast_rate'), value_type=float)
```

Without this you get `InvalidParameterTypeException`.

</details>

<details>
<summary>Hint 4 — the YAML node name</summary>

The top-level key in the YAML must match the `name=` you gave the node in the
launch file — `slow_counter`, not `configurable_counter`. A mismatch is
silently ignored.

</details>

<details>
<summary>Hint 5 — "file not found"</summary>

`setup.py` must install both `launch/` and `config/`, and you must rebuild
after adding the entry.

</details>

---

## Solution

`my_exercises/launch/counter_app.launch.py`:

```python
#!/usr/bin/env python3
"""Exercise 06 - start the whole counter application with one command."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Never hard-code a path. This finds the INSTALLED copy of the file.
    config = os.path.join(
        get_package_share_directory('my_exercises'),
        'config',
        'slow_counter.yaml')

    fast_rate_arg = DeclareLaunchArgument(
        'fast_rate',
        default_value='5.0',
        description='publish_frequency of the fast counter, in Hz.')

    # A LaunchConfiguration is a placeholder resolved at launch time, and it
    # always resolves to a STRING. publish_frequency was declared as a double,
    # so ParameterValue does the conversion for us.
    fast_rate = ParameterValue(LaunchConfiguration('fast_rate'), value_type=float)

    fast_counter = Node(
        package='my_exercises',
        executable='configurable_counter',
        name='fast_counter',                 # overrides the name in the code
        output='screen',
        parameters=[{
            'publish_frequency': fast_rate,
            'step': 1,
        }],
        remappings=[('counter', 'fast/counter')],
    )

    slow_counter = Node(
        package='my_exercises',
        executable='configurable_counter',   # the SAME executable
        name='slow_counter',                 # different name, so no collision
        output='screen',
        parameters=[config],
        remappings=[('counter', 'slow/counter')],
    )

    subscriber = Node(
        package='my_exercises',
        executable='counter_subscriber',
        name='counter_subscriber',
        output='screen',
        remappings=[('counter', 'fast/counter')],
    )

    # Anything not in this list never starts - with no error at all.
    return LaunchDescription([
        fast_rate_arg,
        fast_counter,
        slow_counter,
        subscriber,
    ])
```

`my_exercises/config/slow_counter.yaml`:

```yaml
# The key must match the node's RUNTIME name, i.e. the name= in the launch
# file - not the name in super().__init__().
slow_counter:
  ros__parameters:
    start_value: 1000
    step: 10
    publish_frequency: 0.5
    enabled: true
```

`my_exercises/setup.py`:

```python
import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'my_exercises'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Both of these are required, or ros2 launch cannot find the files.
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@example.com',
    description='Exercise solutions.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'robot_news_station = my_exercises.robot_news_station:main',
            'counter_publisher = my_exercises.counter_publisher:main',
            'counter_subscriber = my_exercises.counter_subscriber:main',
            'battery_monitor = my_exercises.battery_monitor:main',
            'auto_charger = my_exercises.auto_charger:main',
            'motor_driver = my_exercises.motor_driver:main',
            'configurable_counter = my_exercises.configurable_counter:main',
        ],
    },
)
```

Build and run:

```bash
cd ~/ros2_ws
colcon build --packages-select my_exercises      # needed: setup.py changed
source install/setup.bash
ros2 launch my_exercises counter_app.launch.py
```

---

## Why it is written this way

**Two nodes from one executable.** This is the payoff of never hard-coding
names. The code says `'counter'` and `'configurable_counter'`; the launch file
decides they are `/fast/counter` on `/fast_counter` and `/slow/counter` on
`/slow_counter`. Nothing in the Python changed.

**`remappings` uses relative names on both sides.** `('counter', 'fast/counter')`
— no leading slashes. Add one and you lose the ability to namespace the whole
application later.

**`ParameterValue(..., value_type=float)`.** The most common launch-file error
in ROS 2. Arguments arrive as strings; the node declared a double; the
conversion has to be explicit.

**`get_package_share_directory`.** The YAML lives in `install/`, not `src/`,
once it is built. An absolute path works on your machine and nowhere else.

**The YAML key is `slow_counter`.** Not `configurable_counter`. The key must
match the *runtime* name. This mismatch fails silently — the parameters are
simply ignored, no warning — so it is worth checking deliberately with
`ros2 param get /slow_counter step`.

---

## Try breaking it

Two experiments worth doing, because both failures are silent:

1. Delete `remappings` from the **subscriber** only, rebuild, relaunch.
   Nothing errors. The subscriber just never receives anything. Find it with
   `rqt_graph` and `ros2 node info /counter_subscriber`.

2. Change the YAML key from `slow_counter` to `configurable_counter`,
   relaunch, and run `ros2 param get /slow_counter step`. It is `1`, the
   code default — the file was ignored entirely.

Those two failure modes cost people hours. Ten minutes causing them
deliberately is a good trade.

---

## Going further

- Add `namespace='robot1'` to all three nodes instead of remapping, and
  compare `ros2 topic list`.
- Write the same launch file in XML (`counter_app.launch.xml`) and install it
  with `glob('launch/*.launch.xml')`.
- Add a third counter in a loop:
  ```python
  counters = [Node(..., name='counter_%d' % i) for i in range(3)]
  return LaunchDescription([arg] + counters)
  ```
  That is the reason to use Python over XML.

**Next:** [Exercise 07 — an action](07-action.md)
