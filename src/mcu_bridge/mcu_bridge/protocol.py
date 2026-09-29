"""The text protocol spoken between the PC and the microcontroller.

Every message is one line of plain ASCII ending in a newline, so you can
watch it, and even type it by hand, in the Arduino Serial Monitor:

    board -> PC   S <type> <name> <v1> [v2 ...]   one sensor sample
    board -> PC   I <text>                        info, shown in the ROS log
    board -> PC   E <text>                        error, shown in the ROS log
    PC -> board   M <left> <right>                wheel commands, -1.0 .. 1.0

For example:
    S range front_sonar 0.4210
    S imu imu 0.12 -0.03 9.79 0.001 0.000 -0.002
    M 0.500 -0.500

Nothing in this file imports ROS, so it can be unit-tested anywhere.
"""

from dataclasses import dataclass, field


@dataclass
class SensorSample:
    """One 'S' line from the board."""

    sensor_type: str
    name: str
    values: list = field(default_factory=list)


@dataclass
class LogLine:
    """One 'I' or 'E' line from the board."""

    level: str
    text: str


def parse_line(line):
    """Turn one line from the board into a SensorSample, a LogLine or None.

    None means the line was empty or malformed. Boards print junk when they
    boot (the ESP32 bootloader does), so bad lines are skipped, not fatal.
    """
    line = line.strip()
    parts = line.split()
    if not parts:
        return None

    kind = parts[0]
    if kind in ('I', 'E'):
        return LogLine(kind, line[1:].strip())

    if kind == 'S' and len(parts) >= 4:
        try:
            values = [float(v) for v in parts[3:]]
        except ValueError:
            return None
        return SensorSample(parts[1], parts[2], values)

    return None


def twist_to_wheels(linear, angular, wheel_separation, max_wheel_speed):
    """Convert a body velocity into left/right wheel commands in -1.0 .. 1.0.

    linear is m/s forward and angular is rad/s anticlockwise, the same as
    geometry_msgs/Twist on /cmd_vel. 1.0 means the wheel's top speed.

    If either wheel would go past its top speed, both are scaled down by the
    same amount, so the robot follows the same curve, only slower.
    """
    left = (linear - angular * wheel_separation / 2.0) / max_wheel_speed
    right = (linear + angular * wheel_separation / 2.0) / max_wheel_speed

    biggest = max(abs(left), abs(right))
    if biggest > 1.0:
        left /= biggest
        right /= biggest
    return left, right


def format_motor_command(left, right):
    """Build the 'M' line that is sent to the board."""
    return 'M %.3f %.3f\n' % (left, right)
