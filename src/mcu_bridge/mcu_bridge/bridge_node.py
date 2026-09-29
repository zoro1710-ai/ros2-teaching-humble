#!/usr/bin/env python3
"""The PC half of the sensor + motor boilerplate.

Run it with:
    ros2 run mcu_bridge mcu_bridge --ros-args -p port:=/dev/ttyUSB0
    ros2 run mcu_bridge mcu_bridge --ros-args -p port:=sim      # no hardware

It does two jobs, and knows nothing about any particular sensor:

    board --"S range front_sonar 0.42"-->  /sensors/front_sonar  (Range)
    /cmd_vel (Twist)  --"M 0.500 0.500"-->  board --> motors

A publisher is created the first time a sensor name is seen, so adding a
sensor on the board is enough to get a new topic here.

Safety: the latest wheel command is re-sent motor_rate times a second. If
/cmd_vel goes quiet for cmd_vel_timeout seconds, the command becomes zero.
The board has its own watchdog too, so unplugging the PC also stops it.
"""

from geometry_msgs.msg import Twist
from mcu_bridge.converters import convert
from mcu_bridge.ports import open_port
from mcu_bridge.protocol import format_motor_command, LogLine, parse_line, twist_to_wheels
import rclpy
from rclpy.node import Node
from std_msgs.msg import Header


class McuBridge(Node):
    """Relays sensor lines to topics, and /cmd_vel to motor lines."""

    def __init__(self):
        super().__init__('mcu_bridge')

        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('wheel_separation', 0.15)
        self.declare_parameter('max_wheel_speed', 0.5)
        self.declare_parameter('cmd_vel_timeout', 0.5)
        self.declare_parameter('motor_rate', 20.0)

        self._device = self.get_parameter('port').value
        self._baud = self.get_parameter('baud').value
        self._wheel_separation = self.get_parameter('wheel_separation').value
        self._max_wheel_speed = self.get_parameter('max_wheel_speed').value
        self._cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value

        self._port = None
        self._buffer = b''
        self._sensor_pubs = {}
        self._wheels = (0.0, 0.0)
        self._last_cmd_vel = None

        self.create_subscription(Twist, 'cmd_vel', self._on_cmd_vel, 10)
        self.create_timer(0.01, self._read_board)
        self.create_timer(1.0 / self.get_parameter('motor_rate').value, self._send_wheels)
        self.create_timer(2.0, self._connect_if_needed)

        self._connect_if_needed()

    # ---- connection --------------------------------------------------------

    def _connect_if_needed(self):
        if self._port is not None:
            return
        try:
            self._port = open_port(self._device, self._baud)
        except (OSError, ImportError) as error:
            self.get_logger().warn(
                'cannot open %s (%s), retrying every 2 s' % (self._device, error),
                throttle_duration_sec=10.0)
            return
        self._buffer = b''
        self.get_logger().info('connected to %s' % self._device)

    def _lost_connection(self, error):
        self.get_logger().error('lost %s: %s' % (self._device, error))
        try:
            self._port.close()
        except OSError:
            pass
        self._port = None

    # ---- board -> ROS ------------------------------------------------------

    def _read_board(self):
        if self._port is None:
            return
        try:
            self._buffer += self._port.read_available()
        except OSError as error:
            self._lost_connection(error)
            return

        # Everything before the last newline is complete lines; keep the rest.
        *lines, self._buffer = self._buffer.split(b'\n')
        for raw in lines:
            self._handle_line(raw.decode('ascii', errors='replace'))

        if len(self._buffer) > 1024:
            # A kilobyte with no newline is not our protocol (wrong baud rate?).
            self.get_logger().warn('no newline in 1 KB of data - is baud %d right?'
                                   % self._baud, throttle_duration_sec=10.0)
            self._buffer = b''

    def _handle_line(self, line):
        item = parse_line(line)
        if item is None:
            return
        if isinstance(item, LogLine):
            if item.level == 'E':
                self.get_logger().error('[board] ' + item.text)
            else:
                self.get_logger().info('[board] ' + item.text)
            return
        self._publish_sample(item)

    def _publish_sample(self, sample):
        header = Header()
        # Stamped on arrival. Serial adds a few ms of delay; fine for teaching.
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = sample.name + '_link'

        try:
            msg = convert(sample, header)
        except (IndexError, ValueError, AssertionError) as error:
            self.get_logger().warn(
                'bad "%s" sample from %s: %s' % (sample.sensor_type, sample.name, error),
                throttle_duration_sec=5.0)
            return

        publisher = self._sensor_pubs.get(sample.name)
        if publisher is None:
            topic = 'sensors/' + sample.name
            publisher = self.create_publisher(type(msg), topic, 10)
            self._sensor_pubs[sample.name] = publisher
            self.get_logger().info('new sensor "%s" (%s) -> /%s [%s]' % (
                sample.name, sample.sensor_type, topic, type(msg).__name__))
        elif publisher.msg_type is not type(msg):
            self.get_logger().warn(
                'sensor "%s" changed type; restart the bridge' % sample.name,
                throttle_duration_sec=5.0)
            return

        publisher.publish(msg)

    # ---- ROS -> board ------------------------------------------------------

    def _on_cmd_vel(self, msg):
        self._wheels = twist_to_wheels(
            msg.linear.x, msg.angular.z, self._wheel_separation, self._max_wheel_speed)
        self._last_cmd_vel = self.get_clock().now()

    def _send_wheels(self):
        if self._port is None:
            return
        left, right = self._wheels
        if self._last_cmd_vel is None:
            left = right = 0.0
        else:
            age = (self.get_clock().now() - self._last_cmd_vel).nanoseconds / 1e9
            if age > self._cmd_vel_timeout:
                left = right = 0.0
        try:
            self._port.write(format_motor_command(left, right).encode('ascii'))
        except OSError as error:
            self._lost_connection(error)

    def stop_motors(self):
        """Send one last zero command before shutting down."""
        if self._port is None:
            return
        try:
            self._port.write(format_motor_command(0.0, 0.0).encode('ascii'))
            self._port.close()
        except OSError:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = McuBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_motors()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
