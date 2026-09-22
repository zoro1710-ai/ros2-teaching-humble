# ROS 2 Humble — from scratch to a walking robot

A hands-on course for **ROS 2 Humble Hawksbill** on **Ubuntu 22.04**, built as
a real colcon workspace. Every concept comes with runnable, commented code you
can break on purpose.

Parts 1–5 teach ROS 2 itself, ending in a multi-node capstone. Part 6 uses it
to build a **four-legged spider bot** that walks, strafes and turns.

```bash
git clone https://github.com/zoro1710-ai/ros2-teaching-humble.git
cd ros2-teaching-humble
rosdep install --from-paths src --ignore-src -y --rosdistro humble
colcon build --symlink-install
source install/setup.bash
ros2 launch ros2_basics_py talker_listener.launch.py
```

No Ubuntu 22.04? `docker build -t ros2-basics -f docker/Dockerfile . && ./docker/run.sh`

Not sure your setup is right? `python3 scripts/verify_setup.py` checks each
thing that commonly breaks and prints the exact fix.

## Start here

**[docs/README.md](docs/README.md)** — the twenty-three lessons, in order.

If you only have an hour, do lessons 00 → 04. That is enough to write a node
that talks to another node, which is most of day-to-day ROS 2.

If you came here for the legged robot, you still need Parts 1–5 first —
Part 6 is built entirely out of them.

## What is in the box

```
src/
├── ros2_basics_interfaces/   custom .msg / .srv / .action definitions
├── ros2_basics_py/           one runnable example per lesson (rclpy)
├── turtle_capstone/          the capstone: catch every turtle that spawns
└── spider_bot/               Part 6: URDF, leg IK, trot gait, cmd_vel bridge
docs/                         the lessons
exercises/                    eight practice problems, with full solutions
scripts/                      verify_setup.py, build.sh, test.sh, clean.sh
docker/                       Ubuntu 22.04 + Humble image, GUI ready
.github/workflows/            CI: builds and tests every push
```

### The examples

| Topic | Run it |
|---|---|
| A minimal node, timers, logging | `ros2 run ros2_basics_py timer_node` |
| Publisher / subscriber | `ros2 run ros2_basics_py talker` + `listener` |
| Topic + service in one node | `number_publisher` + `number_counter` |
| Service server and client | `add_two_ints_server` + `add_two_ints_client 3 4` |
| A node calling another's service | `led_panel` + `battery_node` |
| Custom messages and services | `hardware_status_publisher`, `rectangle_area_server` |
| Parameters, validated and live | `ros2 run ros2_basics_py parameter_demo` |
| Actions with feedback and cancel | `count_until_server` + `count_until_client` |
| QoS incompatibility, on purpose | `qos_publisher` + `qos_subscriber` |
| Executors and callback groups | `ros2 run ros2_basics_py executor_demo` |
| TF2 broadcast and lookup | `ros2 launch ros2_basics_py tf_demo.launch.py` |
| Lifecycle nodes | `ros2 run ros2_basics_py lifecycle_number_publisher` |
| Capstone | `ros2 launch turtle_capstone catch_them_all.launch.py` |

### The spider bot (Part 6)

| Topic | Run it |
|---|---|
| The robot model, joints on sliders | `ros2 launch spider_bot display.launch.py` |
| The trot gait, in RViz, no physics | `ros2 launch spider_bot walk.launch.py` |
| Drive it | `ros2 run teleop_twist_keyboard teleop_twist_keyboard` |
| Full physics + ros2_control | `ros2 launch spider_bot gazebo.launch.py` |
| The leg maths, tested on its own | `pytest src/spider_bot/test/ -v` |

Lessons 17, 20 and 21 need only RViz. Gazebo is a large install and is only
required for lessons 18 and 19:

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
                 ros-humble-ros2-control ros-humble-ros2-controllers
```

## Requirements

- Ubuntu 22.04 LTS and ROS 2 Humble (or the provided Docker image)
- `python3-colcon-common-extensions`, `python3-rosdep`
- `ros-humble-turtlesim` for the capstone
- `ros-humble-xacro`, `ros-humble-joint-state-publisher-gui` for Part 6

Full instructions: [docs/00-install-and-setup.md](docs/00-install-and-setup.md)

## Credits

The structure of Parts 1–5 follows the teaching order used by the
**[Robotics Back-End](https://www.youtube.com/@RoboticsBackEnd)** ROS 2
tutorials — the number publisher/counter pair, the LED panel and battery
nodes, and the "catch them all" turtlesim capstone all come from that
lineage. The code, lessons and exercises here are written from scratch, and
Part 6 is new.

## Contributing

Issues and pull requests welcome — especially corrections and clearer
explanations. CI builds and tests every package on Humble, so keep it green.

## License

MIT — see [LICENSE](LICENSE). Use it for your own teaching freely.
