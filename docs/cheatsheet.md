# Cheat sheet

Every command used in this course, on one page. Ubuntu 22.04 + ROS 2 Humble.

---

## Setup

```bash
source /opt/ros/humble/setup.bash          # the ROS installation
source install/setup.bash                  # your workspace (after building)
echo $ROS_DISTRO                           # -> humble, if sourced
printenv | grep -i ROS                     # what is actually set

export ROS_DOMAIN_ID=42                    # isolate your system (0-101)
export ROS_LOCALHOST_ONLY=1                # do not talk over the network

python3 scripts/verify_setup.py            # this repo's setup checker
```

## Workspace and build

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws

colcon build                                     # build everything
colcon build --symlink-install                   # edit Python without rebuilding
colcon build --packages-select my_pkg            # just one package
colcon build --packages-up-to my_pkg             # it and its dependencies
colcon build --event-handlers console_direct+    # show full compiler output

rm -rf build install log                         # clean slate (./scripts/clean.sh)

rosdep install --from-paths src --ignore-src -y --rosdistro humble
```

**After every build: `source install/setup.bash`.**

## Packages

```bash
ros2 pkg create my_pkg --build-type ament_python --dependencies rclpy std_msgs
ros2 pkg create my_interfaces --build-type ament_cmake
ros2 pkg list
ros2 pkg prefix my_pkg
ros2 pkg executables my_pkg
```

## Running

```bash
ros2 run <package> <executable>
ros2 run <package> <executable> --ros-args -p name:=value
ros2 run <package> <executable> --ros-args -r old_topic:=new_topic
ros2 run <package> <executable> --ros-args -r __node:=new_name
ros2 run <package> <executable> --ros-args -r __ns:=/my_robot
ros2 run <package> <executable> --ros-args --log-level debug
ros2 run <package> <executable> --ros-args --params-file config/params.yaml
```

## Launch

```bash
ros2 launch <package> <file>.launch.py
ros2 launch <package> <file>.launch.py arg:=value
ros2 launch <package> <file>.launch.py --show-args
ros2 launch <package> <file>.launch.py --debug
ros2 launch <file>.launch.py                      # a file path, no package
```

## Nodes

```bash
ros2 node list
ros2 node info /node_name
```

## Topics

```bash
ros2 topic list
ros2 topic list -t                            # with types
ros2 topic info /topic
ros2 topic info /topic --verbose              # QoS of every endpoint
ros2 topic echo /topic
ros2 topic echo /topic --once
ros2 topic echo /topic --field data
ros2 topic hz /topic
ros2 topic bw /topic
ros2 topic delay /topic                       # needs a Header
ros2 topic pub /topic std_msgs/msg/String "{data: 'hi'}" --once
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}}"
ros2 topic find std_msgs/msg/String
```

## Services

```bash
ros2 service list
ros2 service list -t
ros2 service type /service
ros2 service find example_interfaces/srv/AddTwoInts
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 3, b: 4}"
```

## Actions

```bash
ros2 action list
ros2 action list -t
ros2 action info /action -t
ros2 action send_goal /count_until ros2_basics_interfaces/action/CountUntil \
    "{target_number: 5, period: 1.0}"
ros2 action send_goal ... --feedback           # stream progress
```

## Parameters

```bash
ros2 param list
ros2 param list /node
ros2 param get /node key
ros2 param set /node key value
ros2 param describe /node key
ros2 param dump /node                          # snapshot as YAML
ros2 param load /node params.yaml
```

## Interfaces

```bash
ros2 interface list
ros2 interface show geometry_msgs/msg/Twist
ros2 interface proto geometry_msgs/msg/Twist   # YAML skeleton to paste
ros2 interface packages
ros2 interface package std_msgs
```

## Lifecycle

```bash
ros2 lifecycle nodes
ros2 lifecycle get /node
ros2 lifecycle list /node                      # legal transitions right now
ros2 lifecycle set /node configure
ros2 lifecycle set /node activate
ros2 lifecycle set /node deactivate
ros2 lifecycle set /node cleanup
ros2 lifecycle set /node shutdown
```

## TF2

```bash
ros2 run tf2_tools view_frames                 # writes frames.pdf
ros2 run tf2_ros tf2_echo base_link laser
ros2 run tf2_ros tf2_monitor
ros2 run tf2_ros static_transform_publisher \
    --x 0.2 --y 0 --z 0.15 --frame-id base_link --child-frame-id laser
ros2 topic echo /tf_static --once
```

## Recording

```bash
ros2 bag record /topic1 /topic2
ros2 bag record -a -o my_run
ros2 bag info my_run
ros2 bag play my_run
ros2 bag play my_run --rate 0.5 --loop
ros2 bag play my_run --clock                   # then use_sim_time:=true
```

## Tools

```bash
rqt
rqt_graph
ros2 run rqt_console rqt_console
ros2 run rqt_plot rqt_plot /turtle1/pose/x
ros2 run rqt_reconfigure rqt_reconfigure
rviz2
ros2 doctor
ros2 doctor --report
```

## Part 6 — robot description, simulation, control

```bash
# URDF / xacro
xacro src/spider_bot/urdf/spider_bot.urdf.xacro > /tmp/spider.urdf
check_urdf /tmp/spider.urdf                    # prints the link tree
urdf_to_graphiz /tmp/spider.urdf               # writes a PDF of the tree
ros2 param get /robot_state_publisher robot_description

# Gazebo Classic
ros2 launch gazebo_ros gazebo.launch.py
ros2 run gazebo_ros spawn_entity.py -topic robot_description -entity my_robot -z 0.25
ros2 service call /gazebo/pause_physics std_srvs/srv/Empty
ros2 service call /gazebo/unpause_physics std_srvs/srv/Empty
ros2 topic echo /gazebo/model_states --once    # ground truth pose

# ros2_control
ros2 control list_controllers
ros2 control list_controllers -v               # with claimed interfaces, in order
ros2 control list_hardware_interfaces
ros2 run controller_manager spawner joint_state_broadcaster
ros2 run controller_manager spawner leg_position_controller
ros2 control set_controller_state leg_position_controller inactive
ros2 topic pub /leg_position_controller/commands std_msgs/msg/Float64MultiArray \
    "{data: [0.0, 0.2, -1.7, 0.0, 0.2, -1.7, 0.0, 0.2, -1.7, 0.0, 0.2, -1.7]}" --once

# driving anything that takes /cmd_vel
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.08}, angular: {z: 0.3}}"
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"        # stop
```

## Testing

```bash
colcon test
colcon test --packages-select my_pkg
colcon test-result --all --verbose             # the actual failures
colcon test --return-code-on-test-failure      # for CI
pytest src/my_pkg/test/test_x.py -v            # fast, during development
```

---

## rclpy snippets

```python
# the skeleton
import rclpy
from rclpy.node import Node


class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')


def main(args=None):
    rclpy.init(args=args)
    node = MyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
```

```python
# publisher / subscriber
self._pub = self.create_publisher(String, 'chatter', 10)
msg = String(); msg.data = 'hi'; self._pub.publish(msg)

self._sub = self.create_subscription(String, 'chatter', self.on_msg, 10)

# timer
self._timer = self.create_timer(0.5, self.on_timer)      # seconds
self._timer.cancel()

# service server
self._srv = self.create_service(AddTwoInts, 'add', self.on_request)
def on_request(self, request, response):
    response.sum = request.a + request.b
    return response                                       # never forget this

# service client (non-blocking — use this inside nodes)
self._cli = self.create_client(AddTwoInts, 'add')
if self._cli.service_is_ready():
    future = self._cli.call_async(request)
    future.add_done_callback(self.on_response)

# parameters
self.declare_parameter('rate', 1.0)
value = self.get_parameter('rate').value
self.add_on_set_parameters_callback(self.on_param_change)

# logging
self.get_logger().info('x = %d' % x)
self.get_logger().warn('spammy', throttle_duration_sec=2.0)

# time
stamp = self.get_clock().now().to_msg()
```

```python
# multi-threaded executor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

group = ReentrantCallbackGroup()
self.create_timer(0.1, self.cb, callback_group=group)

executor = MultiThreadedExecutor()
executor.add_node(node)
executor.spin()
```

```python
# QoS
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data

latched = QoSProfile(depth=1,
                     reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
```

## Launch snippets

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('rate', default_value='2.0'),
        Node(
            package='my_pkg',
            executable='my_node',
            name='my_node',
            namespace='robot1',
            output='screen',
            parameters=[{'rate': ParameterValue(LaunchConfiguration('rate'),
                                                value_type=float)}],
            remappings=[('chatter', 'robot1/chatter')],
        ),
    ])
```

## Interface syntax

```
# my_package/msg/MyMessage.msg
float64 value          # not "double", not "float"
int64 count            # not "int"
string label
bool flag
float64[] samples      # variable-length array
std_msgs/Header header # embedded message
```

```
# my_package/srv/MyService.srv
int64 request_field
---
bool success
string message
```

```
# my_package/action/MyAction.action
int64 goal_field
---
int64 result_field
---
int64 feedback_field
```

---

Back to [the course index](README.md) ·
[troubleshooting](troubleshooting.md) · [glossary](glossary.md)
