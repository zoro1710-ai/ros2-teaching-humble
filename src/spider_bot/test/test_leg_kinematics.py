"""Lesson 20 - unit tests for the leg maths, with no ROS involved.

Run just these:
    pytest src/spider_bot/test/test_leg_kinematics.py -v

Or as part of the workspace:
    colcon test --packages-select spider_bot
    colcon test-result --all --verbose

Every test here runs in milliseconds because leg_kinematics.py imports
nothing from rclpy. That is the payoff for keeping the maths out of the node
(lesson 14).

The central trick: we have forward kinematics AND inverse kinematics, so
each one checks the other. If FK(IK(p)) == p for a lot of different p, both
are almost certainly right.
"""

import math

import pytest

from spider_bot.leg_kinematics import (GEOMETRY, LEG_MOUNTS, LegUnreachable,
                                       body_to_leg, forward_kinematics,
                                       inverse_kinematics,
                                       neutral_foot_in_body)

# Foot positions in the leg frame that the robot actually uses.
REACHABLE_POINTS = [
    (0.16, 0.00, -0.12),     # the neutral stance
    (0.18, 0.05, -0.10),
    (0.12, -0.03, -0.15),
    (0.20, 0.00, -0.05),
    (0.14, 0.02, -0.14),
    (0.10, -0.06, -0.10),
]


@pytest.mark.parametrize('point', REACHABLE_POINTS)
def test_ik_then_fk_returns_the_same_point(point):
    """IK and FK must be exact inverses for any reachable foot position."""
    angles = inverse_kinematics(GEOMETRY, *point)
    recovered = forward_kinematics(GEOMETRY, *angles)

    for expected, actual in zip(point, recovered):
        assert actual == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize('angles', [
    (0.0, 0.5, -1.8),
    (0.3, 0.2, -1.2),
    (-0.4, 0.8, -2.0),
    (0.6, -0.1, -1.5),
])
def test_fk_then_ik_returns_the_same_angles(angles):
    """FK then IK recovers the angles, for the knee-down branch.

    Only knee-down (a negative tibia angle) round-trips, because IK always
    picks that solution. That is a deliberate choice, not a bug - see the
    docstring in inverse_kinematics.
    """
    point = forward_kinematics(GEOMETRY, *angles)
    recovered = inverse_kinematics(GEOMETRY, *point)

    for expected, actual in zip(angles, recovered):
        assert actual == pytest.approx(expected, abs=1e-9)


def test_ik_always_returns_knee_down():
    """The tibia angle is never positive, so the leg never bends backwards."""
    for point in REACHABLE_POINTS:
        _, _, tibia = inverse_kinematics(GEOMETRY, *point)
        assert tibia <= 0.0


def test_coxa_angle_points_at_the_target():
    """The coxa angle is just the bearing to the foot in the leg frame."""
    _, _, _ = inverse_kinematics(GEOMETRY, 0.16, 0.0, -0.12)

    coxa, _, _ = inverse_kinematics(GEOMETRY, 0.15, 0.15, -0.12)
    assert coxa == pytest.approx(math.radians(45.0), abs=1e-9)

    coxa, _, _ = inverse_kinematics(GEOMETRY, 0.15, -0.15, -0.12)
    assert coxa == pytest.approx(math.radians(-45.0), abs=1e-9)


def test_too_far_away_raises():
    """A point beyond the leg's reach must raise, not return nonsense."""
    with pytest.raises(LegUnreachable):
        inverse_kinematics(GEOMETRY, 0.50, 0.0, 0.0)


def test_too_close_raises():
    """A point inside the dead zone must raise too."""
    # The femur and tibia differ by 0.04 m, so nothing closer than that to
    # the femur joint is reachable.
    with pytest.raises(LegUnreachable):
        inverse_kinematics(GEOMETRY, GEOMETRY.coxa + 0.01, 0.0, 0.0)


def test_straight_leg_is_reachable():
    """The fully extended pose is exactly at the limit and must not raise."""
    reach = GEOMETRY.coxa + GEOMETRY.femur + GEOMETRY.tibia
    coxa, femur, tibia = inverse_kinematics(GEOMETRY, reach, 0.0, 0.0)

    assert coxa == pytest.approx(0.0, abs=1e-9)
    assert femur == pytest.approx(0.0, abs=1e-6)
    assert tibia == pytest.approx(0.0, abs=1e-6)


def test_every_neutral_stance_is_reachable():
    """The resting pose of all four legs must be inside the workspace.

    If this fails, the robot cannot even stand up, and every gait built on
    top of it is doomed. Worth asserting explicitly.
    """
    for mount in LEG_MOUNTS:
        body_point = neutral_foot_in_body(mount, stance_radius=0.16,
                                          body_height=0.12)
        leg_point = body_to_leg(mount, *body_point)

        # Must not raise.
        coxa, femur, tibia = inverse_kinematics(GEOMETRY, *leg_point)

        # And the coxa should be near zero: the neutral stance points the
        # foot straight out along the leg's own axis.
        assert coxa == pytest.approx(0.0, abs=1e-9)
        assert -math.pi / 2 < femur < math.pi / 2
        assert -2.7 < tibia < 0.2


def test_body_to_leg_undoes_the_mount_transform():
    """A point placed via the mount transform comes back as a pure +x offset."""
    for mount in LEG_MOUNTS:
        body_point = neutral_foot_in_body(mount, stance_radius=0.16,
                                          body_height=0.12)
        leg_x, leg_y, leg_z = body_to_leg(mount, *body_point)

        assert leg_x == pytest.approx(0.16, abs=1e-9)
        assert leg_y == pytest.approx(0.0, abs=1e-9)
        assert leg_z == pytest.approx(-0.12, abs=1e-9)


def test_legs_are_mounted_symmetrically():
    """Sanity check on the mount table itself."""
    assert len(LEG_MOUNTS) == 4

    names = {mount.name for mount in LEG_MOUNTS}
    assert names == {'front_left', 'front_right', 'rear_left', 'rear_right'}

    # The body is symmetric, so the mount positions must sum to zero.
    assert sum(mount.x for mount in LEG_MOUNTS) == pytest.approx(0.0)
    assert sum(mount.y for mount in LEG_MOUNTS) == pytest.approx(0.0)
