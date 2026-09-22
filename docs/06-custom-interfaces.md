# 06 — Custom interfaces (your own .msg, .srv and .action)

**Goal:** stop squeezing your data into `std_msgs/String` and define your own
message, service and action types.

**Code:** [`ros2_basics_interfaces/`](../src/ros2_basics_interfaces/),
[`hardware_status_publisher.py`](../src/ros2_basics_py/ros2_basics_py/hardware_status_publisher.py),
[`sensor_reading_publisher.py`](../src/ros2_basics_py/ros2_basics_py/sensor_reading_publisher.py),
[`rectangle_area_server.py`](../src/ros2_basics_py/ros2_basics_py/rectangle_area_server.py),
[`rectangle_area_client.py`](../src/ros2_basics_py/ros2_basics_py/rectangle_area_client.py)

---

## Why you need this

So far you sent an `Int64` on a topic and asked for a sum with `AddTwoInts`.
Real robots send things like *"temperature 62.1 °C, motors ready, no error"* —
three values that belong together, in one message.

You could pack them into a string like `"62.1;true;ok"` and split it on the
other side. Don't. That string has no type checking, no tooling support, and
the first person who changes the order breaks every subscriber silently.

Instead you **define the type once** and ROS 2 generates the Python (and C++)
classes for you.

---

## The rule that trips everyone up

> **Interfaces must live in their own dedicated package.**

A Python package built with `ament_python` *cannot* generate messages. Message
generation needs `ament_cmake`. So the standard layout — and the one this repo
uses — is:

```
src/
├── ros2_basics_interfaces/   <- ament_cmake, only .msg/.srv/.action files
├── ros2_basics_py/           <- ament_python, your nodes
└── turtle_capstone/          <- ament_python, your nodes
```

Nodes in `ros2_basics_py` then *depend on* `ros2_basics_interfaces`.

If you ever want to create such a package from scratch:

```bash
cd ~/ros2_ws/src
ros2 pkg create my_interfaces --build-type ament_cmake
cd my_interfaces
rm -rf include src          # not needed, this package has no C++ code
mkdir msg srv action
```

---

## Part 1 — Your first message

### The file

Messages live in `msg/` and the filename must be **UpperCamelCase** with a
`.msg` extension.

[`msg/HardwareStatus.msg`](../src/ros2_basics_interfaces/msg/HardwareStatus.msg):

```
# Status of a (pretend) piece of robot hardware.
# Demonstrates a message with several primitive fields.

float64 temperature      # degrees Celsius
bool are_motors_ready    # true when the motor drivers are enabled
string debug_message     # human readable status line
```

That is the whole syntax: one `type name` pair per line, `#` for comments.

### The field types you can use

| In the .msg file | Python type | Note |
|---|---|---|
| `bool` | `bool` | |
| `int8` `int16` `int32` `int64` | `int` | and the `uint*` versions |
| `float32` `float64` | `float` | there is **no** `double` |
| `string` | `str` | |
| `int32[]` | `list` of `int` | variable-length array |
| `int32[5]` | `list` of 5 `int` | fixed-length array |
| `std_msgs/Header` | the Header class | another message, embedded |

Two mistakes beginners make here:

- writing `double` or `float` instead of `float64` — the build fails,
- writing `int` instead of a sized integer — same, the build fails.

### Register it in CMakeLists.txt

A `.msg` file that is not listed here is simply not built. Open
[`CMakeLists.txt`](../src/ros2_basics_interfaces/CMakeLists.txt):

```cmake
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)                   # because we embed a Header
find_package(rosidl_default_generators REQUIRED)  # the generator itself

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/HardwareStatus.msg"
  "msg/SensorReading.msg"
  "msg/Turtle.msg"
  "msg/TurtleArray.msg"
  "srv/ComputeRectangleArea.srv"
  "srv/SetLed.srv"
  "srv/CatchTurtle.srv"
  "action/CountUntil.action"
  DEPENDENCIES std_msgs
)
```

`DEPENDENCIES std_msgs` is required because `SensorReading.msg` embeds
`std_msgs/Header`. Forget it and you get a confusing generator error.

### And in package.xml

[`package.xml`](../src/ros2_basics_interfaces/package.xml) needs four things
that an ordinary package does not:

```xml
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<depend>std_msgs</depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

The `<member_of_group>` line is the one people forget. Without it the
generated interfaces are not exported properly and other packages cannot find
them.

### Build and check it

```bash
cd ~/ros2_ws
colcon build --packages-select ros2_basics_interfaces
source install/setup.bash          # ALWAYS re-source after generating interfaces
ros2 interface show ros2_basics_interfaces/msg/HardwareStatus
```

If `ros2 interface show` says *"unknown package"*, you forgot to re-source.
That is the single most common problem in this lesson.

---

## Part 2 — Publishing your custom message

Full file —
[`hardware_status_publisher.py`](../src/ros2_basics_py/ros2_basics_py/hardware_status_publisher.py):

```python
import random

import rclpy
from rclpy.node import Node
from ros2_basics_interfaces.msg import HardwareStatus


class HardwareStatusPublisher(Node):
    """Publishes a fake hardware status once per second."""

    def __init__(self):
        super().__init__('hardware_status_publisher')

        self._publisher = self.create_publisher(HardwareStatus, 'hardware_status', 10)
        self._timer = self.create_timer(1.0, self.publish_status)

        self.get_logger().info('publishing on /hardware_status')

    def publish_status(self):
        msg = HardwareStatus()
        msg.temperature = round(random.uniform(35.0, 70.0), 2)
        msg.are_motors_ready = msg.temperature < 65.0
        msg.debug_message = (
            'nominal' if msg.are_motors_ready else 'overheating, motors disabled')
        self._publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = HardwareStatusPublisher()
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

Only three things differ from the publisher in lesson 04:

- `from ros2_basics_interfaces.msg import HardwareStatus` — the import path is
  always `<package>.msg` for messages, `<package>.srv` for services,
  `<package>.action` for actions. The class name matches the filename.
- `create_publisher(HardwareStatus, 'hardware_status', 10)` — a custom type is
  used exactly like a built-in one. Nothing else changes.
- `msg = HardwareStatus()` then `msg.temperature = ...` — create the object
  empty, then fill the fields one at a time. Every field starts at a sane
  default (`0.0`, `False`, `''`).

`round(..., 2)` matters more than it looks: `temperature` is `float64`, so the
value you assign must be a Python `float`. Assigning an `int` like `62` raises
`AssertionError: The 'temperature' field must be of type 'float'`.

### The package.xml of the *node* package

`ros2_basics_py` uses the interfaces, so its
[`package.xml`](../src/ros2_basics_py/package.xml) must declare it:

```xml
<depend>ros2_basics_interfaces</depend>
```

Without it the code may still run on your machine (because you sourced the
workspace) but `rosdep` and CI will not know about the dependency, and colcon
may build the packages in the wrong order.

---

## Part 3 — A message that embeds another message

[`msg/SensorReading.msg`](../src/ros2_basics_interfaces/msg/SensorReading.msg):

```
std_msgs/Header header
string sensor_id
float64 value
string unit
```

`std_msgs/Header` is itself a message containing:

```
builtin_interfaces/Time stamp    # when the data was measured
string frame_id                  # which coordinate frame it belongs to
```

Almost every real sensor message carries one. Those two fields are what let
TF2 ([lesson 12](12-tf2.md)) line data up in time and space.

Filling it in, from
[`sensor_reading_publisher.py`](../src/ros2_basics_py/ros2_basics_py/sensor_reading_publisher.py):

```python
    def publish_reading(self):
        self._t += 0.1

        msg = SensorReading()
        # to_msg() converts the rclpy Time object into builtin_interfaces/Time.
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.sensor_id = self._sensor_id
        msg.value = 9.81 + 0.5 * math.sin(self._t)
        msg.unit = 'm/s^2'

        self._publisher.publish(msg)
```

- `msg.header.stamp` — nested messages are just nested attributes. You do not
  create a `Header()` yourself; it already exists inside `msg`.
- `self.get_clock().now()` returns an `rclpy.time.Time`, which is *not* the
  message type. `.to_msg()` converts it. Forgetting `.to_msg()` is a very
  common error.
- Use `self.get_clock().now()`, never `time.time()`. The node clock respects
  simulated time when `use_sim_time` is true; the wall clock does not.

---

## Part 4 — A custom service

A `.srv` file is two message definitions separated by a line of three dashes:

[`srv/ComputeRectangleArea.srv`](../src/ros2_basics_interfaces/srv/ComputeRectangleArea.srv):

```
# Request: the two sides of a rectangle.
float64 length
float64 width
---
# Response: the area plus a message describing what happened.
float64 area
string message
```

The server —
[`rectangle_area_server.py`](../src/ros2_basics_py/ros2_basics_py/rectangle_area_server.py):

```python
class RectangleAreaServer(Node):
    """Computes length * width, rejecting negative input."""

    def __init__(self):
        super().__init__('rectangle_area_server')

        self._service = self.create_service(
            ComputeRectangleArea, 'compute_rectangle_area', self.on_request)

        self.get_logger().info('compute_rectangle_area server ready')

    def on_request(self, request, response):
        if request.length < 0.0 or request.width < 0.0:
            response.area = 0.0
            response.message = 'length and width must be >= 0'
            self.get_logger().warn(response.message)
            return response

        response.area = request.length * request.width
        response.message = 'ok'
        self.get_logger().info(
            '%.2f x %.2f = %.2f' % (request.length, request.width, response.area))
        return response
```

- The callback receives **two** arguments: a filled-in `request` and an empty
  `response` that ROS created for you.
- You fill `response` and **return it**. Forgetting the `return` leaves the
  caller waiting for a malformed answer — another classic.
- Notice the validation path returns a *response*, not an exception. A service
  that answers "no, and here is why" is far easier to debug than one that
  throws.

The client —
[`rectangle_area_client.py`](../src/ros2_basics_py/ros2_basics_py/rectangle_area_client.py)
— uses the non-blocking pattern from [lesson 05](05-services.md):

```python
    def request_area(self):
        if not self._client.service_is_ready():
            self.get_logger().info('waiting for /compute_rectangle_area ...')
            return

        request = ComputeRectangleArea.Request()
        request.length = round(random.uniform(1.0, 10.0), 2)
        request.width = round(random.uniform(1.0, 10.0), 2)

        future = self._client.call_async(request)
        future.add_done_callback(self.on_response)

    def on_response(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error('call failed: %r' % exc)
            return

        self.get_logger().info(
            'area = %.2f (%s)' % (response.area, response.message))
```

`ComputeRectangleArea.Request()` and `.Response()` are nested classes on the
generated type. That naming is fixed: `<Type>.Request`, `<Type>.Response`, and
for actions `<Type>.Goal`, `<Type>.Result`, `<Type>.Feedback`.

---

## Part 5 — Arrays of custom messages

The capstone needs a list of turtles, so it defines a message *containing*
another custom message:

[`msg/Turtle.msg`](../src/ros2_basics_interfaces/msg/Turtle.msg):

```
string name
float64 x
float64 y
float64 theta
```

[`msg/TurtleArray.msg`](../src/ros2_basics_interfaces/msg/TurtleArray.msg):

```
Turtle[] turtles
```

Inside the same package you refer to `Turtle` with no package prefix. From
another package you would write `ros2_basics_interfaces/Turtle`.

In Python, an array field behaves like a list:

```python
msg = TurtleArray()
msg.turtles = [turtle_a, turtle_b]     # assign a whole list
msg.turtles.append(turtle_c)           # or append
```

---

## Try it

```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
```

The custom message:

```bash
# terminal 1
ros2 run ros2_basics_py hardware_status_publisher
# terminal 2
ros2 topic echo /hardware_status
ros2 interface show ros2_basics_interfaces/msg/HardwareStatus
```

The custom service, driven entirely from the CLI:

```bash
# terminal 1
ros2 run ros2_basics_py rectangle_area_server
# terminal 2
ros2 service call /compute_rectangle_area \
  ros2_basics_interfaces/srv/ComputeRectangleArea "{length: 3.0, width: 4.0}"
# and the rejection path
ros2 service call /compute_rectangle_area \
  ros2_basics_interfaces/srv/ComputeRectangleArea "{length: -1.0, width: 4.0}"
```

Then the node version of the client, and the header example:

```bash
ros2 run ros2_basics_py rectangle_area_client
ros2 run ros2_basics_py sensor_reading_publisher
ros2 topic echo /sensor_reading
```

---

## Common mistakes

**`ModuleNotFoundError: No module named 'ros2_basics_interfaces'`**
You did not `source install/setup.bash` after building, or you built only the
Python package. Run `colcon build`, then source, in that order.

**`ros2 interface show` says the package is unknown.**
Same cause. Re-source.

**The build fails with "Unknown type 'double'".**
Use `float64`. There is no `double`, `int` or `float` in the IDL syntax.

**`AssertionError: The 'x' field must be of type 'float'`**
You assigned an `int` to a `float64` field. Write `2.0`, not `2`, or wrap the
value with `float(...)`.

**You added a .msg file and nothing changed.**
Add it to `rosidl_generate_interfaces` in `CMakeLists.txt`, then rebuild. Files
that are not listed are not generated.

**You put the .msg inside your Python package.**
It will be ignored. Interfaces need an `ament_cmake` package.

**It worked, then a later build broke it.**
Delete the stale artefacts: `./scripts/clean.sh` (or `rm -rf build install log`)
and build again. Renamed or deleted interfaces leave ghosts behind.

---

## Recap

- Interfaces live in their own `ament_cmake` package.
- `.msg` = one message. `.srv` = request `---` response. `.action` = goal
  `---` result `---` feedback.
- List every file in `rosidl_generate_interfaces`, and declare
  `<member_of_group>rosidl_interface_packages</member_of_group>`.
- Build, **then source**, then use.
- In Python: `from <pkg>.msg import <Type>`, create it empty, fill the fields.

## Exercise

[Exercise 04 — define and use a custom interface](../exercises/04-custom-interface.md)

**Next:** [07 — Parameters](07-parameters.md)
