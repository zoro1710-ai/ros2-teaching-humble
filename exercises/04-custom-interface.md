# Exercise 04 — A custom interface

**After:** [lesson 06 — Custom interfaces](../docs/06-custom-interfaces.md)

---

## The task

Define your own message and service, then use them.

### Requirements

**The interfaces**, in a new `ament_cmake` package called `my_interfaces`:

1. `msg/MotorStatus.msg` with:
   - `string motor_id`
   - `float64 speed_rpm`
   - `float64 temperature`
   - `bool is_healthy`
2. `srv/SetSpeed.srv`:
   - request: `string motor_id`, `float64 target_rpm`
   - response: `bool success`, `string message`

**The node** — `motor_driver`, in your `my_exercises` package:

1. Publishes a `MotorStatus` on `motor_status` at 2 Hz.
2. Serves `set_speed`:
   - reject an unknown `motor_id` (`success: false` and a clear message),
   - reject a `target_rpm` above 3000 or below 0,
   - otherwise set the speed and answer `success: true`.
3. `temperature` rises with speed (any plausible formula) and `is_healthy` is
   false above 80 °C.

### Check yourself

```bash
ros2 interface show my_interfaces/msg/MotorStatus
ros2 interface show my_interfaces/srv/SetSpeed

ros2 run my_exercises motor_driver
ros2 topic echo /motor_status

ros2 service call /set_speed my_interfaces/srv/SetSpeed "{motor_id: 'left', target_rpm: 1500.0}"
ros2 service call /set_speed my_interfaces/srv/SetSpeed "{motor_id: 'left', target_rpm: 9000.0}"
ros2 service call /set_speed my_interfaces/srv/SetSpeed "{motor_id: 'nope', target_rpm: 100.0}"
```

---

## Hints

<details>
<summary>Hint 1 — creating the interfaces package</summary>

```bash
cd ~/ros2_ws/src
ros2 pkg create my_interfaces --build-type ament_cmake
cd my_interfaces
rm -rf include src
mkdir msg srv
```

It must be `ament_cmake`. A Python package cannot generate interfaces.

</details>

<details>
<summary>Hint 2 — the four lines people forget</summary>

In `package.xml`:

```xml
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

In `CMakeLists.txt`, every file must be listed in
`rosidl_generate_interfaces`.

</details>

<details>
<summary>Hint 3 — "unknown package" after building</summary>

`source install/setup.bash`. Always, after generating interfaces.

</details>

<details>
<summary>Hint 4 — type errors when filling the message</summary>

`float64` needs a Python `float`. `1500` is an `int` and will be rejected;
write `1500.0`.

</details>

---

## Solution

### `my_interfaces/msg/MotorStatus.msg`

```
# Current state of one motor.

string motor_id       # which motor this is
float64 speed_rpm     # current speed
float64 temperature   # degrees Celsius
bool is_healthy       # false when the motor is too hot
```

### `my_interfaces/srv/SetSpeed.srv`

```
# Request: which motor, and how fast.
string motor_id
float64 target_rpm
---
# Response: whether it was accepted, and why not if it was refused.
bool success
string message
```

### `my_interfaces/CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.8)
project(my_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MotorStatus.msg"
  "srv/SetSpeed.srv"
)

ament_package()
```

### `my_interfaces/package.xml`

```xml
<?xml version="1.0"?>
<package format="3">
  <name>my_interfaces</name>
  <version>0.0.1</version>
  <description>Interfaces for the exercises.</description>
  <maintainer email="you@example.com">you</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>

  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

### `my_exercises/my_exercises/motor_driver.py`

```python
#!/usr/bin/env python3
"""Exercise 04 - publishes a custom message and serves a custom service."""

import rclpy
from rclpy.node import Node
from my_interfaces.msg import MotorStatus
from my_interfaces.srv import SetSpeed

MAX_RPM = 3000.0
MAX_SAFE_TEMPERATURE = 80.0


class MotorDriver(Node):
    """Simulates two motors and lets their speed be set over a service."""

    def __init__(self):
        super().__init__('motor_driver')

        # motor_id -> current speed
        self._motors = {'left': 0.0, 'right': 0.0}
        self._publish_index = 0

        self._publisher = self.create_publisher(MotorStatus, 'motor_status', 10)
        self._service = self.create_service(SetSpeed, 'set_speed', self.on_set_speed)
        self._timer = self.create_timer(0.5, self.publish_status)

        self.get_logger().info('motor_driver ready with motors: %s'
                               % ', '.join(sorted(self._motors)))

    def temperature_for(self, speed_rpm):
        """Ambient 25 C plus a rise proportional to speed."""
        return 25.0 + speed_rpm * 0.02

    def publish_status(self):
        # Publish one motor per tick, round robin.
        names = sorted(self._motors)
        name = names[self._publish_index % len(names)]
        self._publish_index += 1

        speed = self._motors[name]
        temperature = self.temperature_for(speed)

        msg = MotorStatus()
        msg.motor_id = name
        msg.speed_rpm = speed
        msg.temperature = temperature
        msg.is_healthy = temperature < MAX_SAFE_TEMPERATURE

        self._publisher.publish(msg)

    def on_set_speed(self, request, response):
        if request.motor_id not in self._motors:
            response.success = False
            response.message = 'unknown motor_id %r, expected one of %s' % (
                request.motor_id, sorted(self._motors))
            self.get_logger().warn(response.message)
            return response

        if not 0.0 <= request.target_rpm <= MAX_RPM:
            response.success = False
            response.message = 'target_rpm must be between 0 and %.0f' % MAX_RPM
            self.get_logger().warn(response.message)
            return response

        self._motors[request.motor_id] = request.target_rpm
        response.success = True
        response.message = 'motor %s set to %.1f rpm' % (
            request.motor_id, request.target_rpm)
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = MotorDriver()
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

### `my_exercises/package.xml`

```xml
  <depend>my_interfaces</depend>
```

### Build

```bash
cd ~/ros2_ws
colcon build
source install/setup.bash            # required, every time interfaces change
ros2 interface show my_interfaces/msg/MotorStatus
```

---

## Why it is written this way

**Interfaces in a separate package.** `ament_python` cannot generate them. It
also means other projects can depend on your types without dragging in your
node code.

**The service answers "no" instead of throwing.** Both rejection paths return
a filled `response` with `success: false` and a message a human can read. A
service that raises leaves the caller with a useless generic failure.

**Every rejection is logged as a warning.** When someone reports "the motor
does not spin", the answer is already in the log.

**`float` everywhere.** `0.0`, `3000.0`, `25.0` — because the fields are
`float64`. Assigning an `int` raises a type assertion at publish time.

**Validation constants at the top.** `MAX_RPM` and `MAX_SAFE_TEMPERATURE` are
named, not buried in the code. In a real node these would be parameters — see
[exercise 05](05-parameters.md).

---

## Going further

- Add `float64[] recent_speeds` to the message and publish a small history.
- Make `MAX_RPM` a parameter instead of a constant.
- Add a `std_msgs/Header` to `MotorStatus` and set
  `msg.header.stamp = self.get_clock().now().to_msg()`.
- Write a client node that ramps the speed up and down using `call_async`.

**Next:** [Exercise 05 — parameters](05-parameters.md)
