# 15 — Tools and debugging

**Goal:** find out what is actually happening in a running system, instead of
guessing.

---

## The method

When something does not work, do not read your code first. Ask the system what
it thinks is going on, in this order:

```
1. Is the node running?          ros2 node list
2. Does the connection exist?    ros2 topic info /x --verbose
3. Is data flowing?              ros2 topic echo /x     ros2 topic hz /x
4. Is the data right?            ros2 topic echo /x
5. Only now, read the code.
```

Nine times out of ten you find the answer at step 2 or 3: a name typo, a
missing remap, a QoS mismatch, or a node that died on start-up.

---

## `ros2 node`

```bash
ros2 node list                    # who is alive
ros2 node info /number_counter    # everything this node offers and uses
```

`ros2 node info` is the single most underused command in ROS 2. It prints the
node's subscriptions, publishers, services, and actions — with their types.
It is how you confirm a remap worked.

---

## `ros2 topic`

```bash
ros2 topic list                                   # what exists
ros2 topic list -t                                # ... with types
ros2 topic info /chatter --verbose                # publishers, subscribers, QoS
ros2 topic echo /chatter                          # print the data
ros2 topic echo /chatter --once                   # just one message
ros2 topic hz /chatter                            # actual rate
ros2 topic bw /chatter                            # bandwidth
ros2 topic delay /scan                            # latency (needs a Header)
ros2 topic pub /chatter std_msgs/msg/String "{data: 'test'}" --once
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}}"
```

`topic pub` and `topic echo` together let you test half a system before the
other half exists. Writing a subscriber? Feed it with `topic pub`. Writing a
publisher? Watch it with `topic echo`. No extra code.

---

## `ros2 service` and `ros2 action`

```bash
ros2 service list
ros2 service list -t
ros2 service type /add_two_ints
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 3, b: 4}"

ros2 action list
ros2 action info /count_until -t
ros2 action send_goal /count_until ros2_basics_interfaces/action/CountUntil \
    "{target_number: 5, period: 1.0}" --feedback
```

The YAML argument follows the message structure. Nested fields nest:
`"{linear: {x: 0.5}, angular: {z: 0.2}}"`.

Tip: run `ros2 interface show <type>` first and fill in the fields you see.

---

## `ros2 param`

```bash
ros2 param list
ros2 param describe /parameter_demo publish_frequency
ros2 param get /parameter_demo robot_name
ros2 param set /parameter_demo publish_frequency 5.0
ros2 param dump /parameter_demo > params.yaml        # snapshot the current config
```

`param dump` is how you capture a tuning session into a YAML file you can load
next time.

---

## `ros2 interface`

```bash
ros2 interface list
ros2 interface show geometry_msgs/msg/Twist
ros2 interface show ros2_basics_interfaces/srv/SetLed
ros2 interface proto geometry_msgs/msg/Twist      # a ready-to-paste YAML skeleton
ros2 interface packages
```

Before you invent a message, check whether one already exists. Standard types
mean RViz, rqt and rosbag understand your data for free.

---

## rqt — the graphical side

```bash
rqt                            # the full suite
rqt_graph                      # who talks to whom
ros2 run rqt_console rqt_console      # filterable log viewer
ros2 run rqt_plot rqt_plot            # live numeric plots
ros2 run rqt_reconfigure rqt_reconfigure   # every parameter, with sliders
```

**`rqt_graph`** is the fastest way to spot a wiring mistake. Two nodes that
should be connected but sit as separate islands means a name mismatch. Uncheck
"Debug" and select "Nodes/Topics (all)" to see unconnected topics too.

**`rqt_console`** beats scrolling a terminal when several nodes are logging at
once — you can filter by node and by severity.

**`rqt_plot`** takes a topic field path:

```bash
ros2 run rqt_plot rqt_plot /turtle1/pose/x /turtle1/pose/y
```

---

## rosbag2 — record and replay

```bash
ros2 bag record /chatter /number_count       # named topics
ros2 bag record -a                           # everything
ros2 bag record -a -o my_run                 # into a named folder

ros2 bag info my_run
ros2 bag play my_run
ros2 bag play my_run --rate 0.5 --loop
```

This is how you debug something that only happens on the real robot: record on
the robot, replay at your desk, as many times as you like.

When replaying data that carries timestamps, nodes should use simulated time:

```bash
ros2 bag play my_run --clock
ros2 run my_pkg my_node --ros-args -p use_sim_time:=true
```

A mismatch here is a classic cause of TF extrapolation errors — some nodes on
wall time, others on bag time.

---

## Logging from your code

```python
self.get_logger().debug('detail nobody needs by default')
self.get_logger().info('normal operation')
self.get_logger().warn('something is odd but we continue')
self.get_logger().error('this operation failed')
self.get_logger().fatal('the node cannot continue')
```

`INFO` and above are printed by default. To see debug output:

```bash
ros2 run ros2_basics_py timer_node --ros-args --log-level timer_node:=debug
ros2 run ros2_basics_py timer_node --ros-args --log-level debug     # everything
```

Two helpers that save your terminal in a 100 Hz callback:

```python
self.get_logger().info('spammy', throttle_duration_sec=2.0)   # at most every 2 s
self.get_logger().info('startup detail', once=True)           # only the first time
```

Log rather than `print()`. Logs carry the node name and timestamp, they can be
filtered by level, and they show up in `rqt_console` and the launch log files.

---

## `ros2 doctor`

```bash
ros2 doctor
ros2 doctor --report
```

Checks your installation and network setup. `--report` prints the middleware
in use, the `ROS_DOMAIN_ID`, network interfaces and package versions — the
first thing to paste when asking for help.

---

## The multi-machine gotchas

Two ROS 2 systems on the same network see each other by default. That means a
colleague's nodes can appear in your `ros2 node list` — and interfere.

```bash
export ROS_DOMAIN_ID=42        # pick 0-101; every machine that must talk uses the same
export ROS_LOCALHOST_ONLY=1    # isolate yourself completely (Humble)
```

Put your choice in `~/.bashrc`. When two machines cannot see each other, check
in this order: same `ROS_DOMAIN_ID`, `ROS_LOCALHOST_ONLY` not set, same
`RMW_IMPLEMENTATION`, firewall open for multicast.

---

## A worked example

**Symptom:** `number_counter` prints nothing.

```bash
$ ros2 node list
/number_counter                      # the publisher is missing entirely
```

Start it, and try again:

```bash
$ ros2 topic list
/my_number                           # not /number — someone remapped it
/number_count

$ ros2 topic info /my_number --verbose
Publisher count: 1
  QoS profile: RELIABLE, VOLATILE, KEEP_LAST 10
Subscription count: 0                # nothing is listening
```

Found it in two commands, without opening an editor: the publisher is
remapped, the counter is not. Fix the launch file
([lesson 08](08-launch-files.md)).

---

## A cheat sheet of first questions

| Symptom | First command |
|---|---|
| "my node does nothing" | `ros2 node list` — did it even start? |
| "no data on my topic" | `ros2 topic info /x --verbose` — counts and QoS |
| "the service call hangs" | `ros2 service list` — does the name exist? |
| "the parameter is ignored" | `ros2 param get /node key` — is it what you set? |
| "TF lookup fails" | `ros2 run tf2_tools view_frames` |
| "it works alone, not in launch" | `ros2 node info /x` — check remaps |
| "it works for me, not for them" | `ros2 doctor --report`, `ROS_DOMAIN_ID` |

More in [troubleshooting.md](troubleshooting.md), and every command in one
place in the [cheat sheet](cheatsheet.md).

**Next:** [16 — Capstone: catch them all](16-capstone-catch-them-all.md)
