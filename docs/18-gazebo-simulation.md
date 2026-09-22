# 18 — Simulating it in Gazebo

**Goal:** put the robot in a world with gravity, contacts and friction, so
that a bad gait actually falls over instead of looking fine in RViz.

**Code:** [`gazebo.launch.py`](../src/spider_bot/launch/gazebo.launch.py),
the `<gazebo>` blocks in
[`spider_bot.urdf.xacro`](../src/spider_bot/urdf/spider_bot.urdf.xacro)

---

## RViz is not a simulator

This is the most important sentence in this lesson.

**RViz draws what you tell it.** If your gait publishes joint angles that
would make the robot fall over, RViz shows the robot standing calmly with its
legs in a silly position. It has no physics, no gravity, no ground.

**Gazebo computes what would happen.** Gravity pulls, feet touch the ground,
friction pushes back, and the body moves — or tips over.

You need both. RViz for "are my angles what I intended", Gazebo for "would
this robot actually walk".

---

## Install

Humble pairs with **Gazebo Classic 11**:

```bash
sudo apt install ros-humble-gazebo-ros-pkgs \
                 ros-humble-gazebo-ros2-control \
                 ros-humble-ros2-control \
                 ros-humble-ros2-controllers
```

It is a big download. Everything in lessons 17, 20 and 21 works without it —
which is why `package.xml` does not list it as a hard dependency.

> **A note on versions.** Gazebo Classic is deprecated in favour of the new
> Gazebo (formerly Ignition), which pairs with Humble as "Fortress" via
> `ros_gz`. Classic is used here because it has far more beginner-level
> material and examples. The concepts transfer directly; the package and
> plugin names change.

---

## What the URDF needs for physics

Three additions turn a description into something simulatable.

### 1. Mass and inertia on every link

```xml
<xacro:macro name="box_inertia" params="mass x y z">
  <inertial>
    <mass value="${mass}"/>
    <inertia
      ixx="${mass * (y*y + z*z) / 12.0}" ixy="0.0" ixz="0.0"
      iyy="${mass * (x*x + z*z) / 12.0}" iyz="0.0"
      izz="${mass * (x*x + y*y) / 12.0}"/>
  </inertial>
</xacro:macro>
```

That is the standard box inertia formula, written once as a macro and reused
by every link.

A link with no `<inertial>` is silently dropped or given a default that makes
the simulation unstable. If your robot explodes on spawn — parts flying apart
at t=0 — check here first. Wildly wrong inertias (a 1 kg link with an inertia
of 1e-9) are the usual cause.

### 2. Friction on the feet

```xml
<gazebo reference="front_left_foot">
  <mu1>1.2</mu1>
  <mu2>1.2</mu2>
  <material>Gazebo/Black</material>
</gazebo>
```

`mu1` and `mu2` are the friction coefficients in the two tangential
directions. Without them the feet are ice skates: the gait runs perfectly and
the robot goes nowhere, or slowly slides sideways.

If your robot walks in simulation but drifts, tune these before you touch the
gait.

Note `<gazebo reference="...">` blocks are **ignored by RViz and by
`check_urdf`**. They only mean something once Gazebo parses the model.

### 3. Collision geometry

Already there from [lesson 17](17-urdf-and-robot-description.md). Keep it
primitive — spheres for feet, cylinders for legs. A collision mesh with
10,000 triangles per leg will drop your simulation to 0.1× real time.

---

## The launch file, and the ordering problem

Starting a simulated robot is the first time launch **order** really matters.

```
1. Gazebo must be running
2. ... then the robot can be spawned into it
3. ... then the controllers can be loaded onto the robot
4. ... then the gait can start sending commands
```

Launch files start everything at once by default. `RegisterEventHandler` is
how you say "then":

```python
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit

        RegisterEventHandler(OnProcessExit(
            target_action=spawn,
            on_exit=[load_joint_state_broadcaster])),
```

Read it as: *when the `spawn` process exits, start
`load_joint_state_broadcaster`.* `spawn_entity.py` exits as soon as the robot
is in the world, which makes it a convenient "done" signal.

[`gazebo.launch.py`](../src/spider_bot/launch/gazebo.launch.py) chains four
stages this way. Skip the chaining and the controller spawners race the
simulator, fail to find a `controller_manager`, and exit — leaving you with a
robot that just lies there.

### Spawning

```python
    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                   '-entity', 'spider_bot',
                   '-z', '0.25'],
    )
```

- **`-topic robot_description`** reuses the *same* description
  `robot_state_publisher` is serving. One model, one source of truth — never
  maintain a separate SDF.
- **`-entity`** is the name inside Gazebo.
- **`-z 0.25`** drops the robot in slightly above the ground. Spawn it at
  `z=0` and the feet start already intersecting the floor; the physics engine
  resolves that by launching your robot into the air.

### Simulated time

```python
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}],
```

Gazebo publishes `/clock`. Every node in a simulation must be told to follow
it with `use_sim_time: true`, or half your system runs on wall time and half
on simulation time. The symptom is TF extrapolation errors that make no
sense — see [lesson 12](12-tf2.md).

Set it on **every** node in the launch file. Forgetting one is a classic.

---

## Try it

```bash
ros2 launch spider_bot gazebo.launch.py
```

Gazebo opens, the robot drops in and the legs start cycling. Expect it to be
unimpressive the first time: real gait tuning is [lesson 21](21-gait-generation.md).

Check the simulation is actually feeding ROS:

```bash
ros2 topic list | grep -E 'clock|joint_states'
ros2 topic echo /clock --once
ros2 topic hz /joint_states
ros2 control list_controllers          # needs ros2_control, lesson 19
```

Look at the simulation's own view:

```bash
ros2 service call /gazebo/pause_physics std_srvs/srv/Empty
ros2 service call /gazebo/unpause_physics std_srvs/srv/Empty
ros2 topic echo /gazebo/model_states --once     # where the robot really is
```

`/gazebo/model_states` is ground truth — where the body *actually* is in the
world. On a real robot you would never have this; in simulation it is how you
check whether your odometry and state estimation are lying to you.

### Experiments worth doing

1. **Set `mu1`/`mu2` to `0.05`** in the xacro, rebuild, relaunch. The gait is
   unchanged and the robot goes nowhere. That is what a friction problem
   looks like — and why "tune the gait" would have been the wrong reaction.
2. **Set `body_mass` to `15.0`.** The legs buckle. Effort limits and gains are
   not free parameters.
3. **Spawn at `-z 0.05`.** Watch the robot get flung. Now you know that
   failure mode.
4. **Pause physics and drag the robot** in the Gazebo GUI, then unpause.
   Recovery behaviour, for free.

---

## Common mistakes

**The robot explodes or vibrates on spawn.**
Bad inertias, or spawned intersecting the ground. Check `<inertial>` values
are physically plausible and raise the spawn height.

**The robot is invisible in Gazebo but fine in RViz.**
Missing `<collision>` or `<inertial>`. RViz only needs `<visual>`.

**The legs move but the robot does not go anywhere.**
Friction. Set `mu1`/`mu2` on the feet.

**`Service /spawn_entity unavailable`.**
Gazebo was not running yet. That is the ordering problem — use
`RegisterEventHandler`.

**`waiting for service /controller_manager/list_controllers`, forever.**
The `gazebo_ros2_control` plugin did not load. Check the `<plugin>` block in
the URDF, and that the YAML path in it resolves.

**TF extrapolation errors everywhere in simulation.**
A node is missing `use_sim_time: true`.

**Everything runs at 0.05× real time.**
Collision meshes are too detailed, or the physics step is too small. Use
primitive collision shapes.

---

## Recap

- RViz draws; Gazebo computes. You need both, for different questions.
- Physics needs `<inertial>` on every link, sensible `<collision>` shapes, and
  friction on the feet.
- Spawn from the `robot_description` topic — one model, not two.
- Launch order matters: Gazebo → spawn → controllers → your node. Chain it
  with `RegisterEventHandler(OnProcessExit(...))`.
- `use_sim_time: true` on every node, no exceptions.

**Next:** [19 — ros2_control](19-ros2-control.md)
