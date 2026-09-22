#!/usr/bin/env python3
"""Lesson 19 - send the gait to ros2_control instead of straight to RViz.

Run it as part of the simulation:
    ros2 launch spider_bot gazebo.launch.py

The difference from gait_controller.py is one method.

    gait_controller      publishes /joint_states  -> "the joints ARE here"
    gait_to_controller   publishes commands       -> "please MOVE there"

That distinction is the whole of lesson 19. With no hardware, claiming the
joint positions is fine, and it is what makes walk.launch.py work with
nothing but RViz. The moment real (or simulated) actuators exist, they are
the ones that report /joint_states, and your job is to send them targets.
Publish both and you get two nodes fighting over /joint_states, a jittering
model, and a confusing afternoon.

The command topic and message type come from the controller chosen in
config/spider_bot_controllers.yaml:

    position_controllers/JointGroupPositionController
        topic: /leg_position_controller/commands
        type:  std_msgs/msg/Float64MultiArray

and the order of the array must match the `joints:` list in that file -
which is why LEG_MOUNTS, the YAML and this node all use the same order.
Check it at runtime with:

    ros2 control list_controllers
    ros2 topic info /leg_position_controller/commands
"""

import rclpy
from std_msgs.msg import Float64MultiArray

from spider_bot.gait_controller import GaitController


class GaitToController(GaitController):
    """The same gait, sent to ros2_control as position commands."""

    def __init__(self):
        """Reuse all of GaitController, then add the command publisher."""
        super().__init__()

        self.declare_parameter(
            'command_topic', '/leg_position_controller/commands')
        topic = self.get_parameter('command_topic').value

        self._command_publisher = self.create_publisher(
            Float64MultiArray, topic, 10)

        # The parent class made a /joint_states publisher we must not use
        # here - joint_state_broadcaster owns that topic now. Drop it so it
        # does not show up as a second publisher and confuse the next person
        # reading `ros2 topic info /joint_states`.
        self.destroy_publisher(self._publisher)
        self._publisher = None

        self.get_logger().info('sending position commands to %s' % topic)

    def publish_positions(self, positions):
        """Send the twelve angles as a command array.

        Note what we do NOT do: publish /joint_states. In simulation the
        joint_state_broadcaster does that, reporting what the joints actually
        achieved.
        """
        msg = Float64MultiArray()
        # The order must match the `joints:` list in the controller YAML.
        msg.data = positions
        self._command_publisher.publish(msg)


def main(args=None):
    """Start the controller-facing gait node until Ctrl+C."""
    rclpy.init(args=args)
    node = GaitToController()
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
