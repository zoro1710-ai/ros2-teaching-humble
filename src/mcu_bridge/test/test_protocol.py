"""Unit tests for the parts of mcu_bridge that need no hardware."""

import math

from mcu_bridge.converters import convert
from mcu_bridge.ports import SimulatedPort
from mcu_bridge.protocol import (
    format_motor_command, LogLine, parse_line, SensorSample, twist_to_wheels)
import pytest
from sensor_msgs.msg import Imu, Range
from std_msgs.msg import Float32MultiArray, Header


def test_parse_sensor_line():
    sample = parse_line('S range front_sonar 0.4210\r\n')
    assert sample == SensorSample('range', 'front_sonar', [0.421])


def test_parse_many_values_and_inf():
    sample = parse_line('S imu imu 0 0 9.8 0.1 0.2 inf')
    assert sample.values[:5] == [0.0, 0.0, 9.8, 0.1, 0.2]
    assert math.isinf(sample.values[5])


def test_parse_log_lines():
    assert parse_line('I ready, 2 sensors') == LogLine('I', 'ready, 2 sensors')
    assert parse_line('E mpu6050 not found') == LogLine('E', 'mpu6050 not found')


@pytest.mark.parametrize('line', [
    '', '   ', 'S range front_sonar', 'S range sonar abc', 'hello', '\x00\xff ets Jun 8',
])
def test_bad_lines_are_ignored(line):
    assert parse_line(line) is None


def test_straight_and_spin():
    assert twist_to_wheels(0.25, 0.0, 0.15, 0.5) == (0.5, 0.5)
    left, right = twist_to_wheels(0.0, 2.0, 0.2, 0.5)
    assert left == pytest.approx(-0.4)
    assert right == pytest.approx(0.4)


def test_too_fast_keeps_the_curve():
    left, right = twist_to_wheels(1.0, 2.0, 0.2, 0.5)  # asks for 1.6 and 2.4
    assert right == pytest.approx(1.0)
    assert left == pytest.approx(1.6 / 2.4)  # same ratio, so same curve


def test_motor_command_format():
    assert format_motor_command(0.5, -1.0) == 'M 0.500 -1.000\n'


def test_known_type_becomes_standard_message():
    header = Header(frame_id='front_sonar_link')
    msg = convert(SensorSample('range', 'front_sonar', [0.42]), header)
    assert isinstance(msg, Range)
    assert msg.range == pytest.approx(0.42)
    assert msg.header.frame_id == 'front_sonar_link'

    imu = convert(SensorSample('imu', 'imu', [1, 2, 3, 4, 5, 6]), header)
    assert isinstance(imu, Imu)
    assert imu.angular_velocity.z == 6
    assert imu.orientation_covariance[0] == -1.0


def test_unknown_type_becomes_float_array():
    msg = convert(SensorSample('light', 'ldr', [512.0]), Header())
    assert isinstance(msg, Float32MultiArray)
    assert list(msg.data) == [512.0]


def test_too_few_values_raise():
    with pytest.raises(ValueError):
        convert(SensorSample('imu', 'imu', [1, 2]), Header())


def test_simulated_board_answers_like_the_firmware():
    port = SimulatedPort()
    port._last_sample -= 1.0  # pretend a second has passed
    port.write(b'M 1.000 1.000\n')
    lines = [parse_line(line) for line in port.read_available().decode().splitlines()]

    assert LogLine('I', 'simulated board ready') in lines
    assert LogLine('I', 'motors 1.00 1.00') in lines
    names = {item.name for item in lines if isinstance(item, SensorSample)}
    assert names == {'front_sonar', 'ldr'}
