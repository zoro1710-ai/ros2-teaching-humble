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
