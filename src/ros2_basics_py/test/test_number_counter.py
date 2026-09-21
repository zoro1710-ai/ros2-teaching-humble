"""Lesson 14 - unit testing the logic inside a node.

Run just these tests:
    colcon test --packages-select ros2_basics_py
    colcon test-result --all --verbose

Or, much faster while developing, straight from the workspace root:
    pytest src/ros2_basics_py/test/test_number_counter.py

The trick that makes a node testable is keeping the decision-making in plain
methods (accumulate, reset) and letting the ROS callbacks be thin wrappers
around them. Then most of your tests need no middleware at all.
"""

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


def test_reset_clears_the_total(node):
    """reset() puts the counter back to zero."""
    node.accumulate(41)
    node.reset()
    assert node.counter == 0


def test_reset_service_rejects_false(node):
    """Calling the service with data=false must not reset anything."""
    node.accumulate(7)
    request = SetBool.Request()
    request.data = False
    response = node.on_reset_request(request, SetBool.Response())

    assert response.success is False
    assert node.counter == 7


def test_reset_service_resets_on_true(node):
    """Calling the service with data=true resets and reports the old value."""
    node.accumulate(7)
    request = SetBool.Request()
    request.data = True
    response = node.on_reset_request(request, SetBool.Response())

    assert response.success is True
    assert node.counter == 0
    assert '7' in response.message
