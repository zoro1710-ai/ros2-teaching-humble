#!/usr/bin/env python3
"""Lesson 21/22 - turn /cmd_vel into twelve joint angles: a walking gait.

Run it with RViz:
    ros2 launch spider_bot walk.launch.py

Then drive it from another terminal:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
    # or
    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.08}}"

This is the bridge every legged robot needs and no navigation stack provides.
Nav2 outputs /cmd_vel and assumes something downstream can follow it. On a
wheeled robot that is a motor driver. On a legged robot it is this node.

The gait
--------
A trot: diagonal pairs of legs move together.

    phase 0.0   front_left + rear_right   swing, the other two push
    phase 0.5   front_right + rear_left   swing, the other two push

Each leg repeats a cycle of length `cycle_time`:

    stance  (phase <  duty_factor)  foot on the ground, sliding backwards
                                    relative to the body - this is what
                                    actually moves the robot
    swing   (phase >= duty_factor)  foot lifted and carried forwards again

With duty_factor = 0.5 exactly two legs are on the ground at any moment,
which is what makes it a trot rather than a walk.
"""

import math

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from spider_bot.leg_kinematics import (GEOMETRY, LEG_MOUNTS, LegUnreachable,
                                       body_to_leg, inverse_kinematics,
                                       neutral_foot_in_body)

#: Phase offset of each leg within the cycle. Diagonal pairs match.
TROT_PHASES = {
    'front_left': 0.0,
    'rear_right': 0.0,
    'front_right': 0.5,
    'rear_left': 0.5,
}

#: Below these values we treat the command as "stop and stand still".
LINEAR_DEADBAND = 0.005      # m/s
ANGULAR_DEADBAND = 0.02      # rad/s


class GaitController(Node):
    """Generates a trot gait and publishes the resulting joint angles."""

    def __init__(self):
        """Declare parameters, build the joint name list and start the loop."""
        super().__init__('gait_controller')

        self.declare_parameter('cycle_time', 0.8)
        self.declare_parameter('duty_factor', 0.5)
        self.declare_parameter('step_height', 0.04)
        self.declare_parameter('body_height', 0.12)
        self.declare_parameter('stance_radius', 0.16)
        self.declare_parameter('max_linear_speed', 0.15)
        self.declare_parameter('max_angular_speed', 0.8)
        self.declare_parameter('update_rate', 50.0)

        self._cycle_time = self.get_parameter('cycle_time').value
        self._duty = self.get_parameter('duty_factor').value
        self._step_height = self.get_parameter('step_height').value
        self._body_height = self.get_parameter('body_height').value
        self._stance_radius = self.get_parameter('stance_radius').value
        self._max_linear = self.get_parameter('max_linear_speed').value
        self._max_angular = self.get_parameter('max_angular_speed').value
        update_rate = self.get_parameter('update_rate').value

        # The commanded body velocity, most recently received on /cmd_vel.
        self._vx = 0.0
        self._vy = 0.0
        self._wz = 0.0

        # How far through the gait cycle we are, in [0, 1).
        self._phase = 0.0
        self._period = 1.0 / update_rate

        # Joint names, in the exact order we will fill the position array.
        self._joint_names = []
        for mount in LEG_MOUNTS:
            self._joint_names.append('%s_coxa_joint' % mount.name)
            self._joint_names.append('%s_femur_joint' % mount.name)
            self._joint_names.append('%s_tibia_joint' % mount.name)

        # Where each foot rests when the robot is standing still.
        self._neutral = {
            mount.name: neutral_foot_in_body(
                mount, self._stance_radius, self._body_height)
            for mount in LEG_MOUNTS
        }

        self._publisher = self.create_publisher(JointState, 'joint_states', 10)
        self._subscription = self.create_subscription(
            Twist, 'cmd_vel', self.on_cmd_vel, 10)
        self._timer = self.create_timer(self._period, self.control_loop)

        self.get_logger().info(
            'gait_controller running at %.0f Hz, cycle %.2f s, body height %.2f m'
            % (update_rate, self._cycle_time, self._body_height))

    # ------------------------------------------------------------------
    # inputs
    # ------------------------------------------------------------------
    def on_cmd_vel(self, msg):
        """Store the latest velocity command, clamped to what the gait can do.

        Callbacks stay tiny: store and return. All the work happens on the
        timer, at a fixed rate, which is what makes the motion predictable.
        """
        self._vx = self.clamp(msg.linear.x, self._max_linear)
        self._vy = self.clamp(msg.linear.y, self._max_linear)
        self._wz = self.clamp(msg.angular.z, self._max_angular)

    @staticmethod
    def clamp(value, limit):
        """Constrain `value` to +/- `limit`."""
        return max(-limit, min(limit, value))

    def is_stopped(self):
        """True when the command is small enough to just stand still."""
        return (abs(self._vx) < LINEAR_DEADBAND
                and abs(self._vy) < LINEAR_DEADBAND
                and abs(self._wz) < ANGULAR_DEADBAND)

    # ------------------------------------------------------------------
    # the gait
    # ------------------------------------------------------------------
    def foot_velocity(self, neutral_x, neutral_y):
        """Return how fast this foot must travel over the ground, in body frame.

        A foot planted on the ground has to cancel the body's motion. For a
        pure translation every foot moves at -v. Add a rotation and each foot
        also has to sweep around the turning centre:

            v_point = v_body + omega x r

        In 2D, omega x r is (-omega * ry, omega * rx).
        """
        vx = self._vx - self._wz * neutral_y
        vy = self._vy + self._wz * neutral_x
        return (vx, vy)

    def foot_target(self, mount, phase):
        """Return this foot's target position (x, y, z) in the body frame."""
        neutral_x, neutral_y, neutral_z = self._neutral[mount.name]

        if self.is_stopped():
            return (neutral_x, neutral_y, neutral_z)

        vx, vy = self.foot_velocity(neutral_x, neutral_y)

        # How far the foot travels during one stance phase. The foot starts
        # a stance half a stride ahead and finishes half a stride behind.
        stance_time = self._cycle_time * self._duty
        stride_x = vx * stance_time
        stride_y = vy * stance_time

        if phase < self._duty:
            # Stance: on the ground, sliding from +half a stride to -half.
            progress = phase / self._duty
            offset_x = stride_x * (0.5 - progress)
            offset_y = stride_y * (0.5 - progress)
            lift = 0.0
        else:
            # Swing: in the air, carried from -half a stride back to +half.
            progress = (phase - self._duty) / (1.0 - self._duty)
            offset_x = stride_x * (progress - 0.5)
            offset_y = stride_y * (progress - 0.5)
            # A half sine: zero at lift-off and at touch-down, highest in the
            # middle. Smooth in and out, which matters on real hardware.
            lift = self._step_height * math.sin(math.pi * progress)

        return (neutral_x + offset_x, neutral_y + offset_y, neutral_z + lift)

    def compute_joint_positions(self):
        """Advance the gait one tick and return the twelve joint angles.

        Kept separate from publishing so that it can be unit tested without
        any middleware, and so gait_to_controller.py can reuse it unchanged.
        """
        # Advance the phase. Standing still freezes it so the robot always
        # starts walking from the same pose.
        if not self.is_stopped():
            self._phase = (self._phase + self._period / self._cycle_time) % 1.0

        positions = []

        for mount in LEG_MOUNTS:
            leg_phase = (self._phase + TROT_PHASES[mount.name]) % 1.0

            body_x, body_y, body_z = self.foot_target(mount, leg_phase)
            leg_x, leg_y, leg_z = body_to_leg(mount, body_x, body_y, body_z)

            try:
                coxa, femur, tibia = inverse_kinematics(
                    GEOMETRY, leg_x, leg_y, leg_z)
            except LegUnreachable as exc:
                # Never let a geometry error kill the control loop. Hold the
                # leg still this tick and tell the operator to slow down.
                self.get_logger().warn(
                    '%s cannot reach its target: %s' % (mount.name, exc),
                    throttle_duration_sec=2.0)
                coxa, femur, tibia = self.neutral_angles(mount)

            positions.extend([coxa, femur, tibia])

        return positions

    def control_loop(self):
        """Compute the gait and publish it. Subclasses change how it is sent."""
        self.publish_positions(self.compute_joint_positions())

    def publish_positions(self, positions):
        """Publish the angles as a JointState, for RViz and TF.

        gait_to_controller.py overrides this to send commands to
        ros2_control instead (lesson 19).
        """
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self._joint_names
        msg.position = positions
        self._publisher.publish(msg)

    def neutral_angles(self, mount):
        """Joint angles for this leg's resting stance, used as a safe fallback."""
        body_x, body_y, body_z = self._neutral[mount.name]
        leg_x, leg_y, leg_z = body_to_leg(mount, body_x, body_y, body_z)
        return inverse_kinematics(GEOMETRY, leg_x, leg_y, leg_z)


def main(args=None):
    """Start the gait controller until Ctrl+C."""
    rclpy.init(args=args)
    node = GaitController()
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
