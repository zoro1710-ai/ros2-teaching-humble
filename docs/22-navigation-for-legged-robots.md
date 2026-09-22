# 22 — Navigation for legged robots

**Goal:** understand exactly what Nav2 gives you, what it assumes, and which
pieces a legged robot has to supply itself.

**Code:** [`gait_controller.py`](../src/spider_bot/spider_bot/gait_controller.py)
(the `/cmd_vel` half)

---

## The one sentence that matters

> **Nav2 does not drive your robot. It publishes `/cmd_vel` and assumes
> something downstream can follow it.**

On a wheeled robot that something is a motor driver — usually
`diff_drive_controller`, which ships with ros2_control. On a legged robot,
**that something is your gait controller**, and nobody is going to write it
for you.

That is why [lesson 21](21-gait-generation.md) exists, and why
`gait_controller` subscribes to `/cmd_vel` and not to something bespoke:

```
   Nav2   ──/cmd_vel──>   gait_controller   ──>   IK   ──>   12 joint angles
(wheeled robots stop here and hand /cmd_vel to a motor driver)
```

Build that bridge and a large amount of the ROS ecosystem starts working on
your spider bot for free. Skip it, and none of it does.

---

## What Nav2 actually is

A pipeline of pluggable pieces:

```
  goal pose
     │
     ▼
  planner          global path around known obstacles       (Dijkstra, A*)
     │
     ▼
  controller       follow that path, avoid new obstacles    (DWB, RPP, MPPI)
     │
     ▼
  /cmd_vel         velocity commands
     │
     ▼
  YOUR ROBOT       ← the part Nav2 does not do
```

Plus:
- **costmaps** — a 2D grid of "how bad is it to be here", built from sensors
- **behaviour tree** — the logic tying it together (retry, back up, spin,
  wait)
- **recoveries** — what to do when stuck
- **AMCL** — localisation within a known map

What Nav2 needs from you is a short, specific list:

| Requirement | Where it comes from |
|---|---|
| the `map → odom → base_link` TF chain | localisation + odometry |
| `/odom` (`nav_msgs/Odometry`) | your state estimation |
| a sensor on a costmap topic (`LaserScan` or `PointCloud2`) | lidar or depth camera |
| a robot footprint | config — a radius or polygon |
| something that consumes `/cmd_vel` | **your gait controller** |

Notice what is *not* on the list: wheels. Nav2 does not care how you move, as
long as you move when asked and report where you are.

---

## The four things that are genuinely harder on legs

### 1. Odometry — there are no wheel encoders

A wheeled robot integrates wheel rotations. You have no wheels.

Options, worst to best:

- **Open-loop integration.** Assume the robot achieved what `/cmd_vel` asked,
  and integrate that. Trivial to write, and it drifts badly — feet slip, the
  robot is pushed, a leg misses. Fine for a first demo, not for navigation.
- **Leg odometry.** While a foot is planted it is a fixed point in the world,
  so the body's motion is the negative of the foot's motion in body frame.
  You already know which feet are in stance — the gait decided. Much better,
  and still drifts when feet slip.
- **IMU fusion.** Combine leg odometry with an IMU using
  `robot_localization` (an EKF). This is the standard answer.
- **Visual or lidar odometry.** `rtabmap`, or lidar scan matching. Most
  accurate, most CPU.

In practice: leg odometry + IMU through `robot_localization`, publishing
`odom → base_link`, and a SLAM or AMCL layer publishing `map → odom`.

**A wrinkle specific to legs:** a walking robot's body bobs and rolls. Mount
the lidar on `base_link` and your "2D" scan sweeps the floor and the ceiling
by turns, filling the costmap with phantom obstacles. Either stabilise the
body attitude in the gait, or filter the scan by the IMU-measured tilt.

### 2. A legged robot is not a rigid footprint

Nav2's costmap models the robot as a circle or a polygon. Your robot's feet
land *outside* the body outline — that is the point of legs.

A foot can safely land on a spot Nav2 marked as lethal (a small hole a wheel
would fall into), and the body can safely pass over an obstacle a wheeled
robot could not.

The pragmatic starting point: set the footprint to a circle that encloses the
whole leg span, and accept that you are more conservative than you need to be.
Foothold-aware planning is a research area, not a config option.

### 3. Holonomic motion

Your gait handles `linear.y` — strafing — with no extra work, because the
stride is a vector ([lesson 21](21-gait-generation.md)). Most Nav2 controllers
default to differential drive and never use it.

To take advantage, choose a controller that supports holonomic motion (DWB
can be configured for it, MPPI handles it) and tell it so. Otherwise your
robot will laboriously turn to face a direction it could simply step towards.

### 4. Terrain

Nav2's world is a 2D plane. Legs exist to handle ground that is not. Rough
terrain needs an **elevation map** (`grid_map`, `elevation_mapping`) and a
foothold planner selecting where each foot lands.

That is well past this course — but it is the reason serious legged robots do
not just run stock Nav2.

---

## A realistic build order

Do not start with Nav2. Each of these is useful on its own, and each one is
required by the next.

**Stage 1 — teleop.** You are here.

```bash
ros2 launch spider_bot walk.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

If keyboard teleop is not smooth and predictable, nothing downstream will be.

**Stage 2 — odometry.** Publish `/odom` and the `odom → base_link` transform
from leg odometry. Test: walk a 2 m square, come back, and see how far the
estimate has drifted. Under 10% is a reasonable start.

**Stage 3 — an IMU.** Add it to the URDF, simulate it with the Gazebo IMU
plugin, and fuse it with `robot_localization`. Test: pick the robot up and
tilt it; the estimate should follow.

**Stage 4 — a lidar.** Add it to the URDF with the Gazebo ray sensor plugin,
publishing `/scan`. Test: see obstacles in RViz where they actually are.

**Stage 5 — SLAM.** `slam_toolbox` in online async mode. Drive around with
teleop and build a map. This is where bad odometry shows up as a smeared,
double-walled map — fix stage 2 before continuing.

```bash
sudo apt install ros-humble-slam-toolbox
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
```

**Stage 6 — Nav2.** Only now.

```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true
```

Set a goal in RViz with **2D Goal Pose** and watch `/cmd_vel` appear. Your
gait controller is already subscribed.

```bash
ros2 topic echo /cmd_vel        # this is Nav2 talking to your gait
```

Expect months, not a weekend. Every stage is debuggable on its own, which is
the whole reason for the order.

---

## Testing the bridge without Nav2

Before installing anything, prove your gait consumes `/cmd_vel` the way Nav2
will produce it: continuously, at ~20 Hz, with mixed linear and angular
components.

```bash
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.08}, angular: {z: 0.3}}"
```

The robot should trace a smooth arc. Then check the three behaviours Nav2
depends on:

```bash
# 1. It stops when told to stop.
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"

# 2. It survives a command it cannot achieve.
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 5.0}}"
#    -> clamped to max_linear_speed, no crash, no LegUnreachable storm

# 3. It survives commands changing faster than the gait cycle.
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"
```

A gait controller that passes these is a valid Nav2 consumer.

> **Safety gap worth knowing about:** Nav2 stops sending `/cmd_vel` when it is
> done — it does not always send a zero. And if the node crashes, nothing
> arrives at all. A real robot needs a **watchdog**: if no `/cmd_vel` has
> arrived for, say, 0.5 s, stop. Add it before you put this on hardware.

---

## Honest scope

What you can do after this course:

- describe a legged robot and see it in RViz
- simulate it with physics
- drive its joints through ros2_control
- solve leg IK
- generate a trot gait
- accept `/cmd_vel` from anything, including Nav2

What still stands between that and a robot navigating your flat:

| Missing | Rough effort |
|---|---|
| leg odometry + IMU fusion | 2–3 weeks |
| lidar or depth sensing, in sim and real | 1–2 weeks |
| SLAM tuned for a bobbing platform | 2–3 weeks |
| Nav2 tuned for a non-rigid footprint | 2–4 weeks |
| body attitude control (not falling over) | weeks to months |
| real hardware: servos, power, a hardware interface | 1–2 months |

That is a real project, not a weekend. But the layer underneath it — the one
this course ends with — is the layer everything else needs, and it is the one
most tutorials skip.

---

## Where to go next

| Topic | Start here |
|---|---|
| Navigation | [navigation.ros.org](https://navigation.ros.org/) |
| Control framework | [control.ros.org](https://control.ros.org/) |
| Sensor fusion | `robot_localization` docs |
| SLAM | `slam_toolbox` |
| Manipulation | [moveit.ros.org](https://moveit.ros.org/) |
| Legged robotics, seriously | Champ (ROS quadruped), the MIT Cheetah papers, `quad-sdk` |

`champ` is worth a specific mention: an open-source ROS 2 quadruped stack with
gait generation, odometry and Nav2 integration already done. After this
course you have enough background to read it — which is the real goal.

---

## Recap

- Nav2 publishes `/cmd_vel`; it does not move your robot. The gait controller
  is the bridge, and it is yours to write.
- Nav2 needs: the TF chain, `/odom`, a sensor, a footprint, and a `/cmd_vel`
  consumer.
- Legs make four things harder: odometry without encoders, a footprint that
  is not rigid, holonomic motion most controllers ignore, and terrain.
- Build in order: teleop → odometry → IMU → lidar → SLAM → Nav2. Each stage
  is testable alone.
- Add a `/cmd_vel` watchdog before real hardware.

---

**That is the end of the course.** Back to [the index](README.md).

You started with a node that printed a string. You now have a described,
simulated, controlled four-legged robot that walks where it is told. The
remaining work is deep, but it is no longer unfamiliar — it is more nodes,
more topics, more transforms, and better maths in the middle.
