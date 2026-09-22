"""Lesson 21 - tests for the gait itself.

These need rclpy (the gait lives in a Node), so they are slower than the
pure maths tests in test_leg_kinematics.py. They are still worth having:
they answer the question "can this robot actually walk, at every speed I
allow, without tearing a leg off?" - and they answer it in two seconds
instead of by watching a simulator.

    pytest src/spider_bot/test/test_gait_controller.py -v
"""

import math

import pytest
import rclpy

from spider_bot.gait_controller import GaitController, TROT_PHASES
from spider_bot.leg_kinematics import LEG_MOUNTS


@pytest.fixture
def node():
    """Provide a live GaitController and tear it down afterwards."""
    rclpy.init()
    controller = GaitController()
    yield controller
    controller.destroy_node()
    rclpy.shutdown()


def drive(controller, vx=0.0, vy=0.0, wz=0.0):
    """Set the commanded body velocity directly, without a /cmd_vel message."""
    controller._vx = vx
    controller._vy = vy
    controller._wz = wz


def test_publishes_twelve_angles(node):
    """Four legs, three joints each."""
    positions = node.compute_joint_positions()
    assert len(positions) == 12
    assert len(node._joint_names) == 12


def test_joint_names_match_the_urdf_convention(node):
    """The names must be exactly what the URDF and the controller YAML use."""
    assert node._joint_names[:3] == [
        'front_left_coxa_joint',
        'front_left_femur_joint',
        'front_left_tibia_joint',
    ]
    for name in node._joint_names:
        assert name.endswith('_joint')


def test_standing_still_holds_the_neutral_pose(node):
    """With no command the legs must not drift."""
    drive(node, 0.0, 0.0, 0.0)

    first = node.compute_joint_positions()
    for _ in range(100):
        later = node.compute_joint_positions()

    for a, b in zip(first, later):
        assert a == pytest.approx(b, abs=1e-12)


def test_walking_forward_moves_the_legs(node):
    """With a command the joint angles must actually change."""
    drive(node, vx=0.10)

    first = node.compute_joint_positions()
    for _ in range(10):
        later = node.compute_joint_positions()

    assert any(abs(a - b) > 1e-4 for a, b in zip(first, later))


@pytest.mark.parametrize('command', [
    {'vx': 0.15},                    # full speed ahead
    {'vx': -0.15},                   # full speed back
    {'vy': 0.15},                    # full speed sideways
    {'wz': 0.8},                     # spin on the spot
    {'vx': 0.15, 'wz': 0.8},         # the worst case: both at once
    {'vx': -0.1, 'vy': 0.1, 'wz': -0.5},
])
def test_no_leg_goes_out_of_reach_at_any_phase(node, command):
    """Every foot target, through a whole cycle, must be reachable.

    If this fails the gait would silently fall back to the neutral pose
    mid-stride and the robot would stumble. Better to find it here.
    """
    drive(node, **command)

    # One full cycle at the configured update rate, plus a margin.
    ticks = int(node._cycle_time / node._period) + 5

    for _ in range(ticks):
        positions = node.compute_joint_positions()

        assert len(positions) == 12
        for angle in positions:
            assert math.isfinite(angle)


def test_joint_limits_are_respected(node):
    """The angles the gait produces must fit inside the URDF joint limits."""
    drive(node, vx=0.15, wz=0.8)

    ticks = int(node._cycle_time / node._period) + 5

    for _ in range(ticks):
        positions = node.compute_joint_positions()

        for index in range(0, 12, 3):
            coxa, femur, tibia = positions[index:index + 3]
            assert -math.pi / 4 <= coxa <= math.pi / 4
            assert -math.pi / 2 <= femur <= math.pi / 2
            assert -2.7 <= tibia <= 0.2


def test_trot_pairs_are_diagonal(node):
    """A trot lifts diagonal pairs together - that is what makes it a trot."""
    assert TROT_PHASES['front_left'] == TROT_PHASES['rear_right']
    assert TROT_PHASES['front_right'] == TROT_PHASES['rear_left']
    assert TROT_PHASES['front_left'] != TROT_PHASES['front_right']

    # And every leg in the mount table has a phase.
    for mount in LEG_MOUNTS:
        assert mount.name in TROT_PHASES


def test_cmd_vel_is_clamped(node):
    """A command faster than the gait can manage is limited, not obeyed."""
    node._vx = node.clamp(99.0, node._max_linear)
    assert node._vx == pytest.approx(node._max_linear)

    node._wz = node.clamp(-99.0, node._max_angular)
    assert node._wz == pytest.approx(-node._max_angular)


def test_feet_stay_on_the_ground_during_stance(node):
    """A stance foot must be at ground level, or the robot hops."""
    drive(node, vx=0.10)

    mount = LEG_MOUNTS[0]
    # Mid-stance for a leg whose phase offset is 0.0.
    _, _, z = node.foot_target(mount, phase=0.25)
    assert z == pytest.approx(-node._body_height, abs=1e-12)


def test_feet_lift_during_swing(node):
    """A swing foot must leave the ground, and come back down smoothly."""
    drive(node, vx=0.10)

    mount = LEG_MOUNTS[0]
    duty = node._duty

    # Just after lift-off and just before touch-down: barely off the ground.
    _, _, z_start = node.foot_target(mount, phase=duty + 1e-6)
    _, _, z_end = node.foot_target(mount, phase=0.999999)
    assert z_start == pytest.approx(-node._body_height, abs=1e-4)
    assert z_end == pytest.approx(-node._body_height, abs=1e-4)

    # Halfway through the swing: at the full step height.
    _, _, z_mid = node.foot_target(mount, phase=duty + (1.0 - duty) / 2.0)
    assert z_mid == pytest.approx(-node._body_height + node._step_height, abs=1e-9)
