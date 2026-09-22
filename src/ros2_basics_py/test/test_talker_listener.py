"""Lesson 14 - an integration test over the real middleware.

This one actually publishes and receives. It is slower than a unit test, so
keep the number of tests like this small and put the detailed cases in
test_number_counter.py.

Pattern used here:
    * build the nodes under test plus a small helper node that records data,
    * put them all on one executor,
    * spin with a timeout instead of forever,
    * assert on what the helper collected.

Never call rclpy.spin() in a test: if the expected message never arrives the
test hangs instead of failing.
"""

import time

from example_interfaces.msg import Int64
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from ros2_basics_py.number_counter import NumberCounter
from ros2_basics_py.number_publisher import NumberPublisher


class Recorder(Node):
    """Helper node that stores everything published on /number_count."""

    def __init__(self):
        super().__init__('recorder')
        self.received = []
        self.create_subscription(Int64, 'number_count', self._on_message, 10)

    def _on_message(self, msg):
        self.received.append(msg.data)


@pytest.fixture
def ros_context():
    """Start and stop rclpy around a single test."""
    rclpy.init()
    yield
    rclpy.shutdown()


def spin_for(executor, seconds):
    """Spin the executor for a bounded amount of wall time."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        executor.spin_once(timeout_sec=0.05)


def test_counter_accumulates_published_numbers(ros_context):
    """number_publisher -> number_counter -> /number_count adds up correctly."""
    # Defaults: number=2 published at 1 Hz (see number_publisher.py).
    publisher = NumberPublisher()
    counter = NumberCounter()
    recorder = Recorder()

    executor = SingleThreadedExecutor()
    for node in (publisher, counter, recorder):
        executor.add_node(node)

    try:
        spin_for(executor, 3.5)

        assert recorder.received, 'nothing was published on /number_count'
        # Every value must be a multiple of 2 and the series must grow.
        assert recorder.received == sorted(recorder.received)
        assert all(value % 2 == 0 for value in recorder.received)
        assert recorder.received[0] == 2
    finally:
        for node in (publisher, counter, recorder):
            executor.remove_node(node)
            node.destroy_node()
