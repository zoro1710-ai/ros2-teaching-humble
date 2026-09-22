# 05 — Services

**Goal:** write a service server, and write a client that does not deadlock.

**Code:** [`add_two_ints_server.py`](../src/ros2_basics_py/ros2_basics_py/add_two_ints_server.py),
[`add_two_ints_client.py`](../src/ros2_basics_py/ros2_basics_py/add_two_ints_client.py),
[`led_panel.py`](../src/ros2_basics_py/ros2_basics_py/led_panel.py),
[`battery_node.py`](../src/ros2_basics_py/ros2_basics_py/battery_node.py)

---

## The model

```
client  ──── request ────>  server
        <──── response ───
```

One request, one response, one server. Unlike a topic:

- if no server exists, the call simply does not happen,
- the client knows whether it worked,
- **two servers on one service name is a bug**, not a feature.

Use a service for a quick action with an answer. If it takes more than about a
second, or the caller might want to cancel, use an [action](09-actions.md).

---

## The server

```python
from example_interfaces.srv import AddTwoInts

self._service = self.create_service(AddTwoInts, 'add_two_ints', self.on_request)

def on_request(self, request, response):
    response.sum = request.a + request.b
    return response          # you MUST return it
```

The callback receives a pre-made `response` object, fills it in, and returns
it. It runs on the executor thread, so the usual rule applies: do not block.

Test it without writing a client at all:

```bash
ros2 service list
ros2 service type /add_two_ints
ros2 interface show example_interfaces/srv/AddTwoInts
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 3, b: 4}"
```

---

## The client — two correct patterns, one trap

### The trap

```python
response = self._client.call(request)     # BLOCKS until the answer arrives
```

Inside a callback (a timer, a subscription), this **deadlocks**. The response
can only be delivered by the executor, and you are currently occupying the
executor waiting for it. The node freezes, forever, with no error message.

### Pattern A — the one-shot script

For a node whose only job is to make one call, as in
`add_two_ints_client.py`:

```python
future = self._client.call_async(request)
rclpy.spin_until_future_complete(self, future)
response = future.result()
```

This is safe because nothing else is spinning this node.

### Pattern B — inside a node that keeps running

This is what you will actually use, as in `battery_node.py`:

```python
future = self._client.call_async(request)
future.add_done_callback(self.on_response)   # returns immediately

def on_response(self, future):
    try:
        response = future.result()
    except Exception as exc:
        self.get_logger().error('call failed: %r' % exc)
        return
    ...
```

When you need to carry extra context into the callback, bind it with
`functools.partial` — see
[`turtle_spawner.py`](../src/turtle_capstone/turtle_capstone/turtle_spawner.py):

```python
from functools import partial
future.add_done_callback(partial(self.on_spawn_response, name=name))
```

### Waiting for the server

```python
# In a script: block until it appears.
while not self._client.wait_for_service(timeout_sec=1.0):
    self.get_logger().info('waiting for the service ...')

# Inside a running node: never block, just check.
if not self._client.service_is_ready():
    return
```

---

## The complete code

### A server

[`add_two_ints_server.py`](../src/ros2_basics_py/ros2_basics_py/add_two_ints_server.py),
in full:

```python
#!/usr/bin/env python3
"""Lesson 05 - a service server using a ready-made interface."""

from example_interfaces.srv import AddTwoInts
import rclpy
from rclpy.node import Node


class AddTwoIntsServer(Node):
    """Answers /add_two_ints with the sum of the two requested integers."""

    def __init__(self):
        super().__init__('add_two_ints_server')

        # create_service(srv_type, service_name, callback)
        self._service = self.create_service(
            AddTwoInts, 'add_two_ints', self.on_request)

        self.get_logger().info('add_two_ints server ready')

    def on_request(self, request, response):
        response.sum = request.a + request.b
        self.get_logger().info(
            '%d + %d = %d' % (request.a, request.b, response.sum))
        return response


def main(args=None):
    rclpy.init(args=args)
    node = AddTwoIntsServer()
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

Three things to notice:

- `from example_interfaces.srv import AddTwoInts` — services import from
  `<package>.srv`, messages from `<package>.msg`.
- The callback signature is `(self, request, response)` — **two** arguments
  after `self`. ROS builds the empty `response` for you.
- `request.a` and `request.b` come from the top half of the `.srv` file;
  `response.sum` from the bottom half. Run
  `ros2 interface show example_interfaces/srv/AddTwoInts` to see them.

### A server that validates

Real servers reject bad input.
[`led_panel.py`](../src/ros2_basics_py/ros2_basics_py/led_panel.py) does it
like this:

```python
    def on_set_led(self, request, response):
        # Validate the request. A service that returns success=False with a
        # clear reason is far easier to debug than one that throws.
        if not 0 <= request.led_number < len(self._leds):
            response.success = False
            self.get_logger().warn(
                'rejected: led_number %d is out of range' % request.led_number)
            return response

        self._leds[request.led_number] = request.state
        response.success = True
        self.get_logger().info(
            'LED %d -> %s' % (request.led_number, 'ON' if request.state else 'off'))
        self.publish_states()
        return response
```

Both paths fill the response and return it. Neither raises. "No, and here is
why" is always more useful to the caller than an exception.

### The client that keeps running

[`battery_node.py`](../src/ros2_basics_py/ros2_basics_py/battery_node.py) is
the pattern to copy — a node with a timer that also calls a service:

```python
    def set_led(self, led_number, state):
        if not self._client.service_is_ready():
            # Non-blocking check. Blocking here would stall the executor and
            # freeze every other callback in this node.
            self.get_logger().warn('/set_led not available yet, skipping')
            return

        request = SetLed.Request()
        request.led_number = led_number
        request.state = state

        future = self._client.call_async(request)
        future.add_done_callback(self.on_set_led_response)

    def on_set_led_response(self, future):
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - we want to log any failure
            self.get_logger().error('service call failed: %r' % exc)
            return

        if not response.success:
            self.get_logger().warn('led_panel rejected the request')
```

Follow the control flow: `set_led` sends the request and **returns
immediately**. The node carries on running its timer. Some time later — maybe
milliseconds, maybe never — the executor calls `on_set_led_response` with the
answer.

That is the shape of every service call inside a real node. `SetLed.Request()`
creates an empty request; `future.result()` may raise, so it is wrapped.

---

## Try it

### By hand

```bash
ros2 run ros2_basics_py add_two_ints_server
ros2 run ros2_basics_py add_two_ints_client 12 30
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 1, b: 2}"
```

### A node calling another node's service

```bash
ros2 run ros2_basics_py led_panel
ros2 run ros2_basics_py battery_node
ros2 topic echo /led_states
```

Watch the battery drain, the LED switch on, then charge and switch off. Both
nodes were written independently and are coupled only by the service name and
type.

### Resetting the counter from lesson 04

```bash
ros2 run ros2_basics_py number_publisher
ros2 run ros2_basics_py number_counter
ros2 topic echo /number_count
ros2 service call /reset_counter std_srvs/srv/SetBool "{data: true}"
```

---

## Useful ready-made service types

| Type | Use |
|---|---|
| `std_srvs/srv/Empty` | trigger with no arguments and no answer |
| `std_srvs/srv/Trigger` | trigger, returns `success` + `message` |
| `std_srvs/srv/SetBool` | turn something on/off, returns `success` + `message` |
| `example_interfaces/srv/AddTwoInts` | tutorials |

`Trigger` covers a surprising amount of real work. Reach for a custom service
only when you genuinely need custom fields ([lesson 06](06-custom-interfaces.md)).

---

## Common mistakes

**The node froze and there is no error.**
You used the blocking `call()` inside a callback. Switch to pattern B.

**`service not available, waiting again...` forever.**
The name is wrong, or the server is in a different namespace. Check
`ros2 service list`.

**The callback returns nothing.**
`return response` is not optional.

**The response fields are empty.**
You filled in a fresh `Response()` object instead of the one passed in.

**Treating `success: False` as an exception.**
It is not. A well-written server answers with `success=False` and a message
explaining why, as `led_panel.py` does for an out-of-range LED.

---

## Exercise

[Exercise 03 — a service server and client](../exercises/03-service.md)

**Next:** [06 — Custom interfaces](06-custom-interfaces.md)
