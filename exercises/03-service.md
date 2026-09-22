# Exercise 03 — A service

**After:** [lesson 05 — Services](../docs/05-services.md)

---

## The task

A server that resets a counter, and a client that calls it from inside a
running node.

### Requirements

**Node 1 — `battery_monitor`**

1. Holds a battery level that starts at 100 and drops by 5 every second.
2. Publishes it on `battery_level` (`example_interfaces/msg/Int64`).
3. Serves `recharge` using `std_srvs/srv/SetBool`:
   - `data: true` → set the level back to 100, respond `success: true` with a
     message saying what the old level was,
   - `data: false` → change nothing, respond `success: false` with a reason.
4. It must never go below 0.

**Node 2 — `auto_charger`**

1. Subscribes to `battery_level`.
2. When the level drops below 20, calls `/recharge` with `data: true`.
3. **Must not block** — the node has a subscription and must stay responsive.
4. Logs whether the recharge was accepted.

### Check yourself

```bash
ros2 run my_exercises battery_monitor
```

```bash
ros2 service list
ros2 service type /recharge
ros2 service call /recharge std_srvs/srv/SetBool "{data: true}"
ros2 service call /recharge std_srvs/srv/SetBool "{data: false}"
ros2 topic echo /battery_level
```

Then start `auto_charger` and watch the level sawtooth between 100 and ~15.

---

## Hints

<details>
<summary>Hint 1 — the server callback signature</summary>

```python
def on_request(self, request, response):
    ...
    return response          # <- never forget this
```

ROS gives you an empty `response`; you fill it and return it.

</details>

<details>
<summary>Hint 2 — the non-blocking client</summary>

Inside a node that is doing other things, never use `client.call()` or
`wait_for_service()` without a timeout. Use:

```python
if self._client.service_is_ready():
    future = self._client.call_async(request)
    future.add_done_callback(self.on_response)
```

</details>

<details>
<summary>Hint 3 — don't spam the service</summary>

The battery is below 20 for several messages in a row. Keep a flag so you only
send one request per discharge cycle.

</details>

---

## Solution

`my_exercises/my_exercises/battery_monitor.py`:

```python
#!/usr/bin/env python3
"""Exercise 03 - a node that publishes state and serves a reset request."""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool


class BatteryMonitor(Node):
    """Drains a simulated battery and recharges it on request."""

    def __init__(self):
        super().__init__('battery_monitor')

        self._level = 100

        self._publisher = self.create_publisher(Int64, 'battery_level', 10)
        self._service = self.create_service(SetBool, 'recharge', self.on_recharge)
        self._timer = self.create_timer(1.0, self.tick)

        self.get_logger().info('battery_monitor ready, level 100')

    # --- pure logic, easy to unit test ---
    def drain(self, amount):
        """Lower the level by `amount`, never below zero. Returns the new level."""
        self._level = max(0, self._level - amount)
        return self._level

    def recharge(self):
        """Set the level back to full and return the previous value."""
        previous = self._level
        self._level = 100
        return previous

    # --- ROS callbacks ---
    def tick(self):
        level = self.drain(5)

        msg = Int64()
        msg.data = level
        self._publisher.publish(msg)

        if level == 0:
            self.get_logger().error('battery empty')

    def on_recharge(self, request, response):
        if not request.data:
            response.success = False
            response.message = 'set data:=true to actually recharge'
            self.get_logger().warn(response.message)
            return response

        previous = self.recharge()
        response.success = True
        response.message = 'recharged from %d to 100' % previous
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
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

`my_exercises/my_exercises/auto_charger.py`:

```python
#!/usr/bin/env python3
"""Exercise 03 - calls a service from inside a node that keeps running."""

from example_interfaces.msg import Int64
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool

LOW_THRESHOLD = 20


class AutoCharger(Node):
    """Watches /battery_level and asks for a recharge when it gets low."""

    def __init__(self):
        super().__init__('auto_charger')

        # True while a recharge request is in flight, so we ask only once.
        self._request_pending = False

        self._subscription = self.create_subscription(
            Int64, 'battery_level', self.on_level, 10)
        self._client = self.create_client(SetBool, 'recharge')

        self.get_logger().info('auto_charger watching /battery_level')

    def on_level(self, msg):
        if msg.data >= LOW_THRESHOLD:
            # Back to a healthy level: allow the next request.
            self._request_pending = False
            return

        if self._request_pending:
            return

        self.request_recharge(msg.data)

    def request_recharge(self, level):
        # service_is_ready() is the NON-blocking check. wait_for_service()
        # here would freeze this node's subscription callback.
        if not self._client.service_is_ready():
            self.get_logger().warn('/recharge is not available yet')
            return

        self.get_logger().info('level is %d, asking for a recharge' % level)
        self._request_pending = True

        request = SetBool.Request()
        request.data = True

        future = self._client.call_async(request)
        future.add_done_callback(self.on_recharge_response)

    def on_recharge_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - log whatever went wrong
            self.get_logger().error('recharge call failed: %r' % exc)
            self._request_pending = False
            return

        if response.success:
            self.get_logger().info('recharge accepted: %s' % response.message)
        else:
            self.get_logger().warn('recharge refused: %s' % response.message)
            self._request_pending = False


def main(args=None):
    rclpy.init(args=args)
    node = AutoCharger()
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

`setup.py`:

```python
            'battery_monitor = my_exercises.battery_monitor:main',
            'auto_charger = my_exercises.auto_charger:main',
```

---

## Why it is written this way

**`call_async` + `add_done_callback`, never `call()`.** `auto_charger` calls
the service from inside a subscription callback. A blocking `call()` there
would wait for a response that can only be delivered by the very thread that
is waiting — an instant deadlock. Lesson 11 explains this properly.

**`service_is_ready()` instead of `wait_for_service()`.** Same reason: the
blocking wait would freeze the node. Checking and skipping this cycle is the
right move — another message arrives in a second anyway.

**The `_request_pending` flag.** Without it, every message below 20 fires a
new request. Guard against repeat requests whenever a condition stays true
across several callbacks.

**`try/except` around `future.result()`.** The call can fail — the server may
have died between the check and the response. An unhandled exception inside a
done-callback is easy to miss.

**The logic is in `drain()` and `recharge()`, not in the callbacks.** That is
what makes it unit-testable without any middleware
([lesson 14](../docs/14-testing.md)).

---

## Going further

- Write unit tests for `drain()` and `recharge()`, including the floor at 0.
- Replace `SetBool` with a custom service that also reports the level in the
  response ([exercise 04](04-custom-interface.md)).
- Kill `battery_monitor` while `auto_charger` is running. Watch the
  `service_is_ready()` check keep the client alive instead of crashing it.

**Next:** [Exercise 04 — a custom interface](04-custom-interface.md)
