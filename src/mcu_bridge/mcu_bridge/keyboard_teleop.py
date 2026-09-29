#!/usr/bin/env python3
"""Drive anything that listens to /cmd_vel from the keyboard.

Run it with (it needs its own terminal, so not from a launch file):
    ros2 run mcu_bridge keyboard_teleop
    ros2 run mcu_bridge keyboard_teleop --ros-args -r cmd_vel:=/turtle1/cmd_vel

The second line drives turtlesim - test your keys there before a real robot.

The current command is re-published 10 times a second until you press
another key. That steady stream is what lets mcu_bridge treat silence as
"the driver has gone" and stop the motors.
"""

import select
import sys
import termios
import tty

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


HELP = """
Drive with:
        w
    a   s   d        s or space = stop
        x
    q / z : faster / slower
    Ctrl-C : quit (sends a stop first)
"""

# key -> (forward, turn), each -1, 0 or 1. Multiplied by the speed settings.
BINDINGS = {
    'w': (1, 0),
    'x': (-1, 0),
    'a': (0, 1),
    'd': (0, -1),
    's': (0, 0),
    ' ': (0, 0),
}

CTRL_C = '\x03'


class KeyboardTeleop(Node):
    """Turns key presses into a steady stream of Twist messages."""

    def __init__(self):
        super().__init__('keyboard_teleop')

        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('angular_speed', 1.0)
        self.declare_parameter('rate', 10.0)

        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.period = 1.0 / self.get_parameter('rate').value

        self._direction = (0, 0)
        self._publisher = self.create_publisher(Twist, 'cmd_vel', 10)

    def handle_key(self, key):
        """Update the direction or speed from one key press."""
        if key in BINDINGS:
            self._direction = BINDINGS[key]
        elif key == 'q':
            self.linear_speed *= 1.1
            self.angular_speed *= 1.1
        elif key == 'z':
            self.linear_speed *= 0.9
            self.angular_speed *= 0.9
        else:
            return
        # \r rewrites the same line instead of scrolling the terminal.
        sys.stdout.write('\rforward %+d  turn %+d   speed %.2f m/s  %.2f rad/s   '
                         % (*self._direction, self.linear_speed, self.angular_speed))
        sys.stdout.flush()

    def publish(self):
        """Publish the current command once."""
        msg = Twist()
        msg.linear.x = self._direction[0] * self.linear_speed
        msg.angular.z = self._direction[1] * self.angular_speed
        self._publisher.publish(msg)

    def stop(self):
        """Publish a zero command."""
        self._direction = (0, 0)
        self.publish()


def main(args=None):
    if not sys.stdin.isatty():
        print('keyboard_teleop needs a real terminal: start it with ros2 run.')
        return

    rclpy.init(args=args)
    node = KeyboardTeleop()
    saved_terminal = termios.tcgetattr(sys.stdin)
    print(HELP)
    try:
        # Raw mode: each key arrives at once, without waiting for Enter, and
        # Ctrl-C arrives as a normal character, so we can send a stop before
        # quitting instead of being killed by the signal.
        tty.setraw(sys.stdin.fileno())
        while rclpy.ok():
            ready, _, _ = select.select([sys.stdin], [], [], node.period)
            if ready:
                key = sys.stdin.read(1)
                if key == CTRL_C:
                    break
                node.handle_key(key.lower())
            node.publish()
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved_terminal)
        print()
        if rclpy.ok():
            node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
