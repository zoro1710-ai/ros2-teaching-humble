# 14 — Testing

**Goal:** test ROS 2 code the way you would test any other code, and let CI
catch your mistakes before your robot does.

**Code:** [`test_number_counter.py`](../src/ros2_basics_py/test/test_number_counter.py),
[`test_talker_listener.py`](../src/ros2_basics_py/test/test_talker_listener.py),
[`ci.yml`](../.github/workflows/ci.yml)

---

## The trick that makes a node testable

Look again at
[`number_counter.py`](../src/ros2_basics_py/ros2_basics_py/number_counter.py):

```python
    # --- pure logic, kept separate so it can be unit tested without ROS ---
    def accumulate(self, value):
        """Add `value` to the running total and return the new total."""
        self._counter += value
        return self._counter

    def reset(self):
        """Set the running total back to zero."""
        self._counter = 0

    # --- ROS callbacks ---
    def on_number(self, msg):
        total = self.accumulate(msg.data)
        out = Int64()
        out.data = total
        self._publisher.publish(out)
```

The decision-making lives in plain methods. The ROS callback is a thin wrapper
that unpacks a message, calls the logic, and publishes the answer.

Do that and most of your tests need no middleware at all — they are ordinary
Python tests, and they run in milliseconds.

Write the logic *inside* the callback instead and the only way to test it is
to spin up a whole system. That is the difference between a suite you run
every save and one you run never.

---

## Level 1 — unit tests

[`test_number_counter.py`](../src/ros2_basics_py/test/test_number_counter.py):

```python
import pytest
import rclpy
from ros2_basics_py.number_counter import NumberCounter
from std_srvs.srv import SetBool


@pytest.fixture
def node():
    """Provide a live NumberCounter and tear it down afterwards."""
    rclpy.init()
    counter = NumberCounter()
    yield counter
    counter.destroy_node()
    rclpy.shutdown()


def test_starts_at_zero(node):
    """A freshly created counter has not accumulated anything."""
    assert node.counter == 0


def test_accumulate_sums_values(node):
    """accumulate() returns the running total, not just the last value."""
    assert node.accumulate(2) == 2
    assert node.accumulate(3) == 5
    assert node.accumulate(-5) == 0


def test_reset_service_rejects_false(node):
    """Calling the service with data=false must not reset anything."""
    node.accumulate(7)
    request = SetBool.Request()
    request.data = False
    response = node.on_reset_request(request, SetBool.Response())

    assert response.success is False
    assert node.counter == 7
```

Three things to take away:

- **The fixture handles `rclpy.init()` / `shutdown()`.** Doing it per test
  keeps tests isolated; forgetting the shutdown makes the *next* test fail with
  a confusing "context already initialized".
- **No spinning.** The node object is constructed, but nothing runs. You call
  its methods directly.
- **A service callback is just a function.** Build a `Request()`, hand it an
  empty `Response()`, call the callback, assert on what comes back. No client,
  no server, no discovery.

Run them:

```bash
# fast, during development — no build needed with --symlink-install
pytest src/ros2_basics_py/test/test_number_counter.py -v

# the way CI does it
colcon test --packages-select ros2_basics_py
colcon test-result --all --verbose
```

`colcon test` hides failures behind a summary line; `colcon test-result
--verbose` is what actually shows you the assertion. Always run both.

---

## Level 2 — integration tests

Sometimes you do need the real middleware: are these two nodes actually wired
together?

[`test_talker_listener.py`](../src/ros2_basics_py/test/test_talker_listener.py):

```python
class Recorder(Node):
    """Helper node that stores everything published on /number_count."""

    def __init__(self):
        super().__init__('recorder')
        self.received = []
        self.create_subscription(Int64, 'number_count', self._on_message, 10)

    def _on_message(self, msg):
        self.received.append(msg.data)


def spin_for(executor, seconds):
    """Spin the executor for a bounded amount of wall time."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        executor.spin_once(timeout_sec=0.05)


def test_counter_accumulates_published_numbers(ros_context):
    """number_publisher -> number_counter -> /number_count adds up correctly."""
    publisher = NumberPublisher()
    counter = NumberCounter()
    recorder = Recorder()

    executor = SingleThreadedExecutor()
    for node in (publisher, counter, recorder):
        executor.add_node(node)

    try:
        spin_for(executor, 3.5)

        assert recorder.received, 'nothing was published on /number_count'
        assert recorder.received == sorted(recorder.received)
        assert all(value % 2 == 0 for value in recorder.received)
        assert recorder.received[0] == 2
    finally:
        for node in (publisher, counter, recorder):
            executor.remove_node(node)
            node.destroy_node()
```

The pattern, which you can reuse for any pair of nodes:

1. Build the nodes under test **plus a small recorder node** that captures the
   output.
2. Put them all on **one executor** ([lesson 11](11-executors-and-callback-groups.md)).
3. **Spin with a deadline**, never forever.
4. Assert on what the recorder collected.
5. Tear everything down in a `finally`.

> **Never call `rclpy.spin()` in a test.** If the expected message never
> arrives, the test hangs instead of failing, and your CI job sits there until
> it times out. `spin_once(timeout_sec=...)` in a bounded loop is the rule.

Integration tests are slower and flakier than unit tests — discovery takes
time, timing varies on a loaded CI machine. Keep a handful of them for the
wiring, and put the detailed cases in unit tests.

Assert on *properties* rather than exact values where you can. Note how the
test above checks "sorted, all even, starts at 2" instead of demanding exactly
`[2, 4, 6]` — which would fail whenever the CI machine is slow.

---

## Level 3 — the linters you already have

Every package in this repo ships two test files you did not write:

```
test/test_flake8.py     # style and obvious bugs
test/test_pep257.py     # docstring conventions
```

They come from `ros2 pkg create` and run as part of `colcon test`. They are
free correctness checks — unused imports, undefined names, shadowed variables.
Keep them green.

For that to work, `package.xml` needs:

```xml
<test_depend>ament_copyright</test_depend>
<test_depend>ament_flake8</test_depend>
<test_depend>ament_pep257</test_depend>
<test_depend>python3-pytest</test_depend>
```

---

## Continuous integration

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs the whole thing
on every push, inside the official Humble container:

```yaml
    container:
      image: ros:humble-ros-base
```

The steps are exactly what you do locally:

```yaml
      - name: Resolve package dependencies with rosdep
        run: |
          rosdep update --rosdistro humble
          rosdep install --from-paths src --ignore-src -y --rosdistro humble

      - name: Build
        run: |
          source /opt/ros/humble/setup.bash
          colcon build --symlink-install --event-handlers console_direct+

      - name: Test
        run: |
          source /opt/ros/humble/setup.bash
          source install/setup.bash
          colcon test --event-handlers console_direct+ --return-code-on-test-failure
```

Two details that matter:

- **`--return-code-on-test-failure`** — without it `colcon test` exits 0 even
  when tests fail, and your CI badge lies to you.
- **`source install/setup.bash` before testing** — otherwise the test cannot
  import your package or your custom interfaces.

This is also the reason `package.xml` dependencies must be accurate: CI starts
from a bare container, so anything you forgot to declare fails there even
though it works on your machine. That is a feature.

---

## Try it

```bash
cd ~/ros2_ws
colcon test --packages-select ros2_basics_py
colcon test-result --all --verbose
```

Now break something on purpose and watch it get caught:

1. In `number_counter.py`, change `self._counter += value` to
   `self._counter = value`.
2. Run the tests again.

`test_accumulate_sums_values` fails with a clear message, and so does the
integration test. Change it back.

---

## Common mistakes

**`RuntimeError: Failed to create interrupt guard condition` / context errors.**
`rclpy.init()` was called twice, or `shutdown()` was never called. Use a
fixture, one init per test.

**The test hangs forever.**
Something called `rclpy.spin()`, or waited on a future with no timeout. Use
bounded spinning.

**The test passes alone but fails in the suite.**
Leftover state: a node that was not destroyed, or a topic name shared between
tests. Tear down in `finally`, and give test nodes distinct names.

**`ModuleNotFoundError` in CI but not locally.**
A missing `<depend>` or `<test_depend>` in `package.xml`. Your machine has it
installed; the clean container does not.

**`colcon test` says everything passed but you know it did not.**
Run `colcon test-result --all --verbose`, and add
`--return-code-on-test-failure` in CI.

**Flaky timing-based tests.**
Increase the spin window, and assert on properties rather than exact counts.

---

## Recap

- Keep logic in plain methods; keep ROS callbacks thin. That is what makes
  testing possible.
- Unit tests: construct the node, call methods, never spin.
- Integration tests: one executor, a recorder node, bounded spinning.
- `colcon test` then `colcon test-result --all --verbose`.
- CI in the `ros:humble-ros-base` container catches missing dependencies.

**Next:** [15 — Tools and debugging](15-tools-and-debugging.md)
