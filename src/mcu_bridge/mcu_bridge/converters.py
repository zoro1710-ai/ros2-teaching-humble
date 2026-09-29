"""Turn a SensorSample from the board into a ROS message.

The board says what kind of sensor it is in the <type> field of each line.

  * If that type is in CONVERTERS, the bridge publishes a standard message
    such as sensor_msgs/Range. RViz, rqt and other ROS tools understand
    those straight away.
  * Any other type is published as std_msgs/Float32MultiArray. So a brand
    new sensor works on day one without touching this file.

To give a new type a proper message:
    1. write a function  to_xxx(sample, header) -> message
    2. add it to CONVERTERS below
"""

from sensor_msgs.msg import Imu, Range, Temperature
from std_msgs.msg import Float32MultiArray


STANDARD_GRAVITY = 9.80665


def to_range(sample, header):
    """Build sensor_msgs/Range from [distance_m] (HC-SR04, VL53L0X, ...)."""
    msg = Range()
    msg.header = header
    msg.radiation_type = Range.ULTRASOUND
    msg.field_of_view = 0.26  # about 15 degrees, the HC-SR04 cone
    msg.min_range = 0.02
    msg.max_range = 4.0
    # By convention (REP 117) +inf means "nothing in front of me".
    msg.range = sample.values[0]
    return msg


def to_imu(sample, header):
    """Build sensor_msgs/Imu from [ax, ay, az, gx, gy, gz] in m/s^2 and rad/s."""
    ax, ay, az, gx, gy, gz = sample.values[:6]
    msg = Imu()
    msg.header = header
    msg.linear_acceleration.x = ax
    msg.linear_acceleration.y = ay
    msg.linear_acceleration.z = az
    msg.angular_velocity.x = gx
    msg.angular_velocity.y = gy
    msg.angular_velocity.z = gz
    # -1 in the first cell means "this IMU does not report orientation".
    msg.orientation_covariance[0] = -1.0
    return msg


def to_temperature(sample, header):
    """Build sensor_msgs/Temperature from [degrees_celsius]."""
    msg = Temperature()
    msg.header = header
    msg.temperature = sample.values[0]
    return msg


CONVERTERS = {
    'range': to_range,
    'imu': to_imu,
    'temperature': to_temperature,
}


def convert(sample, header):
    """Return the ROS message for one sample.

    Unknown types become Float32MultiArray. That message has no header, so
    the timestamp and frame are lost - one more reason to add a converter.
    """
    converter = CONVERTERS.get(sample.sensor_type)
    if converter is None:
        return Float32MultiArray(data=sample.values)
    return converter(sample, header)
