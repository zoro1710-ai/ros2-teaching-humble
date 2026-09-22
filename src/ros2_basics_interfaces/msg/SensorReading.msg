# A single sensor sample.
# Demonstrates embedding another message type (std_msgs/Header) so the
# reading carries a timestamp and a frame_id.

std_msgs/Header header
string sensor_id
float64 value
string unit
