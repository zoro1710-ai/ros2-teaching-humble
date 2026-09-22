# 08 — Launch files

**Goal:** start a whole application with one command, and wire nodes together
without editing their code.

**Code:** [`talker_listener.launch.py`](../src/ros2_basics_py/launch/talker_listener.launch.py),
[`talker_listener.launch.xml`](../src/ros2_basics_py/launch/talker_listener.launch.xml),
[`number_app.launch.py`](../src/ros2_basics_py/launch/number_app.launch.py),
[`led_battery.launch.py`](../src/ros2_basics_py/launch/led_battery.launch.py),
[`params_demo.launch.py`](../src/ros2_basics_py/launch/params_demo.launch.py)

---

## The problem

A real application is five, ten, twenty nodes. Opening twenty terminals and
typing twenty `ros2 run` commands — each with its own parameters and
remappings — is not a plan.

A launch file starts all of them at once, with their settings, in one command:

```bash
ros2 launch ros2_basics_py talker_listener.launch.py
```

---

## The smallest launch file

[`talker_listener.launch.py`](../src/ros2_basics_py/launch/talker_listener.launch.py):

```python
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    talker = Node(
        package='ros2_basics_py',
        executable='talker',
        name='talker',
        output='screen',
    )

    listener = Node(
        package='ros2_basics_py',
        executable='listener',
        name='listener',
        output='screen',
    )

    return LaunchDescription([talker, listener])
```

Read it from the bottom up:

- **`generate_launch_description()`** — this exact function name is required.
  `ros2 launch` imports your file and calls it. Nothing else runs it.
- **It returns a description; it does not start anything.** Your Python code
  runs once, builds a list of *actions*, and hands that list to the launch
  system, which does the actual starting. This is the mental shift that makes
  launch files click.
- **`Node(...)`** is `launch_ros.actions.Node` — a description of a process to
  start. It is not `rclpy.node.Node`. Two different classes, same name; if
  your launch file throws odd errors, check the import.
- **`package`** is the ROS package, **`executable`** is the name from the
  `console_scripts` list in `setup.py` — not the Python filename.
- **`name`** overrides the node's own name (the string passed to
  `super().__init__`). This is how you run the same executable twice.
- **`output='screen'`** prints the node's log to your terminal. Leave it out
  and the output goes to a log file and you will think the node is dead.

Put every action in the list you return. An action you build but forget to add
to `LaunchDescription` simply never starts — with no error at all.

### Where the file must live

```python
# setup.py
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
```

Launch files are **installed**, not read from `src/`. If `ros2 launch` cannot
find your file, it is almost always this line missing, or you did not rebuild.
Use `--symlink-install` and you can edit the launch file without rebuilding
every time.

---

## Parameters and remapping

[`number_app.launch.py`](../src/ros2_basics_py/launch/number_app.launch.py) is
the one to study — it shows the three features you will use constantly.

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    number_arg = DeclareLaunchArgument(
        'number',
        default_value='4',
        description='Value the publisher sends on /my_number.')

    frequency_arg = DeclareLaunchArgument(
        'frequency',
        default_value='2.0',
        description='Publishing frequency in Hz.')

    number = ParameterValue(LaunchConfiguration('number'), value_type=int)
    frequency = ParameterValue(LaunchConfiguration('frequency'), value_type=float)

    publisher = Node(
        package='ros2_basics_py',
        executable='number_publisher',
        name='my_number_publisher',
        output='screen',
        parameters=[{
            'number': number,
            'publish_frequency': frequency,
        }],
        remappings=[('number', 'my_number')],
    )

    counter = Node(
        package='ros2_basics_py',
        executable='number_counter',
        name='my_number_counter',
        output='screen',
        remappings=[
            ('number', 'my_number'),
            ('number_count', 'my_number_count'),
        ],
    )

    return LaunchDescription([number_arg, frequency_arg, publisher, counter])
```

### `parameters=`

A list of dictionaries and/or YAML file paths. Later entries override earlier
ones, so a common pattern is `parameters=[config_file, {'override': value}]`.

### `remappings=`

```python
remappings=[('number', 'my_number')]
```

Reads as *"wherever this node says `number`, use `my_number` instead."* The
node's own code is untouched.

This is why [lesson 04](04-topics.md) insisted on **relative** topic names.
`'number'` can be remapped; `'/number'` cannot be remapped as easily and
ignores namespaces entirely.

Remapping applies to topics **and** services — see
[`led_battery.launch.py`](../src/ros2_basics_py/launch/led_battery.launch.py),
where both nodes are moved onto `/panel/set_led`:

```python
        remappings=[('set_led', 'panel/set_led')],
```

Remap one side and forget the other, and you get no error at all — just
silence. `ros2 node info /battery_node` and `ros2 service list` are how you
catch it.

### Launch arguments

```python
number_arg = DeclareLaunchArgument('number', default_value='4', description='...')
```

This makes the launch file itself configurable:

```bash
ros2 launch ros2_basics_py number_app.launch.py number:=10 frequency:=4.0
ros2 launch ros2_basics_py number_app.launch.py --show-args    # what can I set?
```

Two rules that catch everyone:

1. **`LaunchConfiguration('number')` is a placeholder, not a value.** It is
   resolved later, when the launch system runs. You cannot print it, compare
   it, or do arithmetic on it inside `generate_launch_description`.
2. **Launch arguments are always strings.** `number_publisher` declared
   `number` as an `int`, so passing the raw string fails with
   `InvalidParameterTypeException`. That is exactly what
   `ParameterValue(..., value_type=int)` fixes — it converts the string to the
   declared type at launch time.

---

## Loading a YAML file

[`params_demo.launch.py`](../src/ros2_basics_py/launch/params_demo.launch.py):

```python
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
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

    return LaunchDescription([parameter_demo])
```

`get_package_share_directory('pkg')` returns the installed
`install/pkg/share/pkg` path, wherever the workspace happens to live. This is
the only correct way to reference a file that ships with a package.

Remember from [lesson 07](07-parameters.md): the node name inside the YAML
must match the `name=` you set here, or the parameters are silently ignored.

---

## The XML flavour

ROS 2 accepts Python, XML and YAML launch files. The same thing in XML —
[`talker_listener.launch.xml`](../src/ros2_basics_py/launch/talker_listener.launch.xml):

```xml
<launch>
  <arg name="chatter_topic" default="chatter"/>

  <node pkg="ros2_basics_py" exec="talker" name="talker" output="screen">
    <remap from="chatter" to="$(var chatter_topic)"/>
  </node>

  <node pkg="ros2_basics_py" exec="listener" name="listener" output="screen">
    <remap from="chatter" to="$(var chatter_topic)"/>
  </node>
</launch>
```

Much shorter, and easier to read when all you do is start nodes and set
parameters. Reach for Python when you need conditionals, loops, or to compute
something before launching.

Note the attribute names differ: `pkg` and `exec`, not `package` and
`executable`. Install `*.launch.xml` in `setup.py` too.

---

## Namespaces: the other way to duplicate a node

```python
    left = Node(package='my_pkg', executable='motor', namespace='left')
    right = Node(package='my_pkg', executable='motor', namespace='right')
```

Every relative name in the node gets the prefix, so you get `/left/cmd`,
`/left/status`, `/right/cmd`, `/right/status` from one unmodified executable.
This is why relative names matter.

---

## Try it

```bash
ros2 launch ros2_basics_py talker_listener.launch.py
```

```bash
# what did that actually create?
ros2 node list
ros2 topic list
```

Now the configurable one:

```bash
ros2 launch ros2_basics_py number_app.launch.py
ros2 topic echo /my_number_count
```

```bash
# same launch file, different behaviour, no code change
ros2 launch ros2_basics_py number_app.launch.py number:=10 frequency:=4.0
ros2 launch ros2_basics_py number_app.launch.py --show-args
```

The service pair, remapped:

```bash
ros2 launch ros2_basics_py led_battery.launch.py
ros2 service list            # note /panel/set_led, not /set_led
ros2 topic echo /led_states
```

And the YAML one:

```bash
ros2 launch ros2_basics_py params_demo.launch.py
ros2 param get /parameter_demo robot_name      # -> "humble_bot", from the file
```

**A useful experiment:** open `led_battery.launch.py`, delete the `remappings`
line from `battery_node` only, rebuild, and launch again. Nothing errors — the
LEDs just never change. Then find it with `ros2 service list` and
`ros2 node info /battery_node`. That debugging loop is the real lesson here.

---

## Common mistakes

**`file 'x.launch.py' was not found`**
The file is not installed. Check the `data_files` entry in `setup.py`, then
rebuild and re-source.

**`ros2 launch` runs but you see no log output.**
Add `output='screen'` to the `Node`.

**Nothing starts, and there is no error.**
You built an action but forgot to put it in the `LaunchDescription([...])` list.

**`InvalidParameterTypeException` when passing a launch argument.**
Launch arguments are strings. Wrap with
`ParameterValue(LaunchConfiguration('x'), value_type=int)` (or `float`/`bool`).

**Two nodes with the same `name=`.**
Both start, both answer to the same name, and everything downstream becomes
unpredictable. Give each one a distinct `name` or a distinct `namespace`.

**A remap works one way only.**
You remapped the publisher but not the subscriber (or the server but not the
client). Both sides must agree.

**You confused `launch_ros.actions.Node` with `rclpy.node.Node`.**
Check the import at the top of the launch file.

---

## Recap

- `generate_launch_description()` returns a `LaunchDescription` of actions.
- `Node(package=, executable=, name=, output='screen')` describes one process.
- `parameters=[...]` sets settings, `remappings=[...]` rewires names,
  `namespace=` prefixes them all.
- `DeclareLaunchArgument` + `LaunchConfiguration` make the launch file itself
  configurable; wrap with `ParameterValue(..., value_type=...)` for non-strings.
- Launch files must be installed by `setup.py`.

## Exercise

[Exercise 06 — launch the whole application](../exercises/06-launch-file.md)

**Next:** [09 — Actions](09-actions.md)
