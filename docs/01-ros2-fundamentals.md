# 01 — ROS 2 fundamentals

**Goal:** understand what ROS 2 actually is, and the four ways nodes talk.

---

## What ROS 2 is

ROS 2 is not an operating system and it is not a library you `import` to get a
robot. It is three things:

1. **A communication layer.** Small programs find each other on the network
   and exchange typed messages without knowing each other's addresses.
2. **A set of conventions.** Standard message types, a standard way to lay out
   a package, a standard place for parameters. Two teams that have never met
   can plug their code together.
3. **A toolbox.** Visualise data (`rviz2`), record and replay it (`ros2 bag`),
   inspect anything at runtime from the CLI (`ros2 topic`, `ros2 node`, ...).

The value is the decoupling. A LIDAR driver publishes `sensor_msgs/LaserScan`.
Whatever consumes it does not care which LIDAR it is, what language the driver
is written in, or which machine it runs on.

## Why ROS 2 and not ROS 1

| | ROS 1 | ROS 2 |
|---|---|---|
| Discovery | central `roscore`; if it dies, everything dies | peer-to-peer over DDS, no single point of failure |
| Transport | custom TCPROS | DDS (an industrial standard) |
| Delivery guarantees | fixed | configurable per topic via QoS |
| Real time | not really | designed for it |
| Multi-robot | painful | native |
| Windows / macOS | unofficial | supported |

Practical consequence: **you never start a master.** Run a node and it finds
its peers by itself.

---

## The five core concepts

### Node

A node is a process that does one job. `camera_driver`, `obstacle_detector`,
`motor_controller`. Keeping nodes small is the whole point: you can restart,
replace or debug one without touching the rest.

```bash
ros2 node list
ros2 node info /talker
```

### Topic — a named, typed stream

Many-to-many, asynchronous, fire-and-forget. The publisher does not know or
care who is listening, and never blocks waiting for them.

Use it for continuous data: sensor readings, velocity commands, state updates.

```
/camera/image_raw   sensor_msgs/Image      30 Hz
/cmd_vel            geometry_msgs/Twist    20 Hz
```

### Service — a request/reply call

One-to-one, synchronous in spirit. The client asks, the server answers exactly
once. If there is no server, nothing happens.

Use it for quick actions with an answer: "reset the odometry", "what is your
serial number", "turn LED 3 on".

**Do not use a service for anything slow.** The caller is stuck waiting, and
cannot cancel.

### Action — a long-running goal

A goal you can watch and cancel. Built on top of three services plus two
topics, but you use a single `ActionServer`/`ActionClient` class.

Use it for: "navigate to the kitchen" (30 seconds, gives progress, might need
cancelling), "pick up the object", "rotate 360°".

### Parameter — a per-node setting

A named value a node declares at startup, readable and (usually) writable at
runtime. Use it for anything you would otherwise hard-code: frame names,
gains, thresholds, device paths.

```bash
ros2 param list
ros2 param set /turtle_controller linear_gain 4.0
```

---

## Which one do I use?

```
Is it a continuous stream of data?              -> topic
Do I need an answer, and it is fast (< ~1 s)?   -> service
Does it take a while, and might need cancelling
  or reporting progress?                        -> action
Is it a setting, not a message?                 -> parameter
```

When in doubt between a service and an action, ask: *would a user want to
cancel this?* If yes, action.

---

## What DDS is doing underneath

DDS (Data Distribution Service) is the middleware ROS 2 speaks. It handles:

- **Discovery.** On startup a node multicasts "I exist, here is what I
  publish and subscribe". Peers reply. This is why there is no master, and
  also why nodes on the same LAN can find each other unintentionally — see
  `ROS_DOMAIN_ID` below.
- **Transport and reliability.** Retransmission, ordering, history.
- **QoS matching.** A publisher and a subscriber connect only if their
  quality-of-service settings are compatible. This is the source of the most
  confusing beginner bug in ROS 2, covered in [lesson 10](10-qos.md).

### ROS_DOMAIN_ID

Every node on the same domain ID (default `0`) on the same network can see
every other one. In a classroom, that means your talker will meet everyone
else's listener. Fix it before you start:

```bash
export ROS_DOMAIN_ID=42        # pick any number 0-101, unique to you
```

Put it in `~/.bashrc` next to the `source` line.

---

## Try it

ROS 2 ships with demo nodes. No building required:

```bash
# terminal 1
ros2 run demo_nodes_cpp talker

# terminal 2
ros2 run demo_nodes_py listener

# terminal 3 — look at what is happening
ros2 node list
ros2 topic list
ros2 topic echo /chatter
ros2 topic info /chatter --verbose
ros2 topic hz /chatter
rqt_graph
```

Notice that the talker is C++ and the listener is Python. Neither knows or
cares. That is the decoupling in action.

---

## Check yourself

- [ ] Why is there no `roscore` in ROS 2?
- [ ] A node needs to report battery percentage every second. Topic, service
      or action?
- [ ] A node needs to run a 20-second self-calibration that the operator can
      abort. Which one?
- [ ] Two students run `talker` on the same network and both listeners get
      double messages. What is the fix?

**Next:** [02 — Workspaces and packages](02-workspaces-and-packages.md)
