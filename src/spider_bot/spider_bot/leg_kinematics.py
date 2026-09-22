#!/usr/bin/env python3
"""Lesson 20 - the maths of one 3-DOF spider leg, with no ROS in sight.

This module is deliberately plain Python. It imports nothing from rclpy, so
you can run it, poke at it and unit test it without a robot, without a
simulator and without sourcing a workspace:

    python3 -c "from spider_bot.leg_kinematics import GEOMETRY, \
inverse_kinematics; print(inverse_kinematics(GEOMETRY, 0.16, 0.0, -0.12))"

Keeping the maths separate from the node is the same trick used in
number_counter.py (lesson 14): decisions in plain functions, ROS callbacks as
thin wrappers around them.

Frames
------
Each leg has its own frame whose origin is the coxa joint:

    +x  points outward, away from the body
    +y  points to the left of that
    +z  points up

so a foot on the ground is at negative z.

Joint angle conventions (these match the axes chosen in the URDF):

    coxa   rotates about +z   positive swings the leg toward +y
    femur  rotates about -y   positive lifts the foot
    tibia  rotates about -y   positive lifts the foot, measured relative
                              to the femur (0 = tibia in line with femur)

The URDF uses "0 -1 0" as the femur and tibia axis precisely so that a
positive angle lifts the foot here. Pick a convention, write it down, and
make the model agree with the code - most kinematics bugs are a sign error
nobody wrote down.
"""

import math

__all__ = [
    'GEOMETRY',
    'LEG_MOUNTS',
    'LegGeometry',
    'LegMount',
    'LegUnreachable',
    'body_to_leg',
    'forward_kinematics',
    'inverse_kinematics',
    'neutral_foot_in_body',
]


class LegUnreachable(ValueError):
    """Raised when a requested foot position is outside the leg's workspace."""


class LegGeometry:
    """The three link lengths of one leg, in metres."""

    def __init__(self, coxa, femur, tibia):
        """Store the link lengths, measured joint centre to joint centre."""
        self.coxa = coxa
        self.femur = femur
        self.tibia = tibia

    @property
    def max_reach(self):
        """Furthest distance from the coxa joint the foot can be placed."""
        return self.coxa + self.femur + self.tibia

    def __repr__(self):
        """Return a readable form, handy when a test fails."""
        return 'LegGeometry(coxa=%.3f, femur=%.3f, tibia=%.3f)' % (
            self.coxa, self.femur, self.tibia)


class LegMount:
    """Where one leg is bolted to the body, and which way it points."""

    def __init__(self, name, x, y, yaw):
        """Store the mount pose of a leg in the body frame."""
        self.name = name
        self.x = x
        self.y = y
        self.yaw = yaw

    def __repr__(self):
        """Return a readable form, handy when a test fails."""
        return 'LegMount(%r, x=%.3f, y=%.3f, yaw=%.3f)' % (
            self.name, self.x, self.y, self.yaw)


#: Link lengths of the robot described in urdf/spider_bot.urdf.xacro.
#: Change them here AND in the xacro, or the model and the maths disagree.
GEOMETRY = LegGeometry(coxa=0.05, femur=0.10, tibia=0.14)

#: The four legs, splayed 45 degrees out from each corner of the body.
#: The order of this list is the order joint names are published in.
LEG_MOUNTS = [
    LegMount('front_left', x=0.12, y=0.08, yaw=math.radians(45.0)),
    LegMount('front_right', x=0.12, y=-0.08, yaw=math.radians(-45.0)),
    LegMount('rear_left', x=-0.12, y=0.08, yaw=math.radians(135.0)),
    LegMount('rear_right', x=-0.12, y=-0.08, yaw=math.radians(-135.0)),
]


def forward_kinematics(geometry, coxa_angle, femur_angle, tibia_angle):
    """Return the foot position (x, y, z) in the leg frame for three angles.

    This is the easy direction: given the joints, where is the foot? It is
    worth implementing even when you only need the inverse, because it gives
    you a way to check the inverse (see test_leg_kinematics.py).
    """
    # Work in the vertical plane the leg lies in, then rotate that plane by
    # the coxa angle. `radius` is the distance from the coxa axis.
    radius = (geometry.coxa
              + geometry.femur * math.cos(femur_angle)
              + geometry.tibia * math.cos(femur_angle + tibia_angle))

    z = (geometry.femur * math.sin(femur_angle)
         + geometry.tibia * math.sin(femur_angle + tibia_angle))

    x = radius * math.cos(coxa_angle)
    y = radius * math.sin(coxa_angle)
    return (x, y, z)


def inverse_kinematics(geometry, x, y, z):
    """Return (coxa, femur, tibia) angles that place the foot at (x, y, z).

    Raises LegUnreachable if the point is outside the leg's workspace, which
    is a real possibility every time you tune a gait. Handle it; do not let
    it crash the control loop.

    There are two solutions (knee up and knee down). We always return the
    knee-down one, which is what a spider leg looks like.
    """
    # 1. The coxa simply points the leg's vertical plane at the target.
    coxa_angle = math.atan2(y, x)

    # 2. Reduce to a 2-link planar problem in that plane.
    radius = math.hypot(x, y)
    planar_x = radius - geometry.coxa        # distance from the femur joint
    reach = math.hypot(planar_x, z)          # straight-line distance to the foot

    longest = geometry.femur + geometry.tibia
    shortest = abs(geometry.femur - geometry.tibia)

    if reach > longest + 1e-9:
        raise LegUnreachable(
            'foot at (%.3f, %.3f, %.3f) is %.3f m from the femur joint, '
            'but the leg only reaches %.3f m' % (x, y, z, reach, longest))

    if reach < shortest - 1e-9:
        raise LegUnreachable(
            'foot at (%.3f, %.3f, %.3f) is %.3f m from the femur joint, '
            'which is inside the %.3f m dead zone' % (x, y, z, reach, shortest))

    # 3. The law of cosines gives the knee angle.
    cos_tibia = ((reach * reach - geometry.femur * geometry.femur
                  - geometry.tibia * geometry.tibia)
                 / (2.0 * geometry.femur * geometry.tibia))

    # Clamp before acos: floating point can push a legal value to 1.0000000002
    # and acos would raise ValueError on a perfectly reachable point.
    cos_tibia = max(-1.0, min(1.0, cos_tibia))

    # Negative = knee down. Flip the sign for the knee-up solution.
    tibia_angle = -math.acos(cos_tibia)

    # 4. The femur angle is "point at the foot" plus the correction for the
    #    fact that the knee is bent.
    femur_angle = (math.atan2(z, planar_x)
                   - math.atan2(geometry.tibia * math.sin(tibia_angle),
                                geometry.femur + geometry.tibia * math.cos(tibia_angle)))

    return (coxa_angle, femur_angle, tibia_angle)


def body_to_leg(mount, x, y, z):
    """Convert a point from the body frame into one leg's frame.

    This is exactly what TF2 would do for you (lesson 12). Doing it by hand
    once is worth it: it is a translation followed by a rotation, and nothing
    more.
    """
    # Translate so the coxa joint is the origin.
    dx = x - mount.x
    dy = y - mount.y

    # Rotate by -yaw to undo the leg's mounting angle.
    cos_yaw = math.cos(-mount.yaw)
    sin_yaw = math.sin(-mount.yaw)

    leg_x = dx * cos_yaw - dy * sin_yaw
    leg_y = dx * sin_yaw + dy * cos_yaw
    return (leg_x, leg_y, z)


def neutral_foot_in_body(mount, stance_radius, body_height):
    """Return where this leg's foot rests when the robot stands still.

    The foot sits `stance_radius` straight out along the leg's own +x axis,
    `body_height` below the body.
    """
    x = mount.x + stance_radius * math.cos(mount.yaw)
    y = mount.y + stance_radius * math.sin(mount.yaw)
    return (x, y, -body_height)
