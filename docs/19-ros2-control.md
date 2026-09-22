# 19 — ros2_control

**Goal:** stop *claiming* joint positions and start *commanding* them, through
the layer that talks to real (or simulated) actuators.

**Code:** [`spider_bot_controllers.yaml`](../src/spider_bot/config/spider_bot_controllers.yaml),
[`gait_to_controller.py`](../src/spider_bot/spider_bot/gait_to_controller.py),
the `<ros2_control>` block in
[`spider_bot.urdf.xacro`](../src/spider_bot/urdf/spider_bot.urdf.xacro)

---

## The distinction this lesson is about

```
gait_controller       publishes /joint_states   →  "the joints ARE at these angles"
gait_to_controller    publishes commands        →  "please MOVE to these angles"
```

In [lesson 21](21-gait-generation.md)'s RViz-only setup, the gait node
publishes `/joint_states` directly. That is a **lie of convenience**: nothing
moved, we just asserted a position and `robot_state_publisher` drew it. For
tuning a gait, that lie is useful — there is no physics to fight.

The moment real actuators exist, they are the ones that know where the joints
are. Your job changes to sending *targets*. Keep publishing `/joint_states`
too and you get two publishers fighting, a jittering model, and a
frustrating afternoon.

---

## What ros2_control is for

Between your gait code and a motor there is a lot of boring, universal work:
a real-time loop, reading encoders, writing commands, enforcing limits,
switching between controllers safely.

ros2_control does that work once, so that the same controller code runs
against Gazebo, against a real robot, and against someone else's robot.

```
  your node
      │ /leg_position_controller/commands  (Float64MultiArray)
      ▼
┌──────────────────────────────────────────────┐
│  controller_manager        (the real-time loop)
│    ├── joint_state_broadcaster   reads  → /joint_states
│    └── leg_position_controller   writes → joint commands
└──────────────────────────────────────────────┘
      │ hardware interface
      ▼
  GazeboSystem  (simulation)   or   YourRobotHardware  (real servos)
```

Swap that bottom box and nothing above it changes. That is the entire value
proposition.

---

## Part 1 — declaring the hardware in the URDF

```xml
<ros2_control name="SpiderBotHardware" type="system">
  <hardware>
    <plugin>gazebo_ros2_control/GazeboSystem</plugin>
  </hardware>

  <joint name="front_left_coxa_joint">
    <command_interface name="position">
      <param name="min">-0.7854</param>
      <param name="max">0.7854</param>
    </command_interface>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
  ...
</ros2_control>
```

Read it as a contract:

- **`<plugin>`** — who actually moves things. `GazeboSystem` for simulation.
  On real hardware you would write a small C++ plugin that talks to your
  servo bus, and change only this line.
- **`<command_interface>`** — what you may *ask* of this joint. `position`
  here; `velocity` and `effort` also exist, and a joint may offer several.
- **`<state_interface>`** — what you can *read back*. Position and velocity.

Twelve joints means twelve of these blocks, so the repo wraps them in a
`leg_control` xacro macro and calls it four times — the same trick as the leg
itself.

Then the plugin that runs the loop inside Gazebo:

```xml
<gazebo>
  <plugin filename="libgazebo_ros2_control.so" name="gazebo_ros2_control">
    <parameters>$(find spider_bot)/config/spider_bot_controllers.yaml</parameters>
  </plugin>
</gazebo>
```

`$(find spider_bot)` is xacro's way of locating the installed package share
directory — the same job `get_package_share_directory` does in Python.

---

## Part 2 — choosing controllers

[`config/spider_bot_controllers.yaml`](../src/spider_bot/config/spider_bot_controllers.yaml):

```yaml
controller_manager:
  ros__parameters:
    update_rate: 200            # Hz - the control loop rate, not the gait rate

    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster

    leg_position_controller:
      type: position_controllers/JointGroupPositionController

leg_position_controller:
  ros__parameters:
    joints:
      - front_left_coxa_joint
      - front_left_femur_joint
      - front_left_tibia_joint
      - front_right_coxa_joint
      ...
```

Two controllers, doing opposite jobs:

**`joint_state_broadcaster`** is not really a controller — it commands
nothing. It reads every joint's state interfaces and publishes
`/joint_states`. It is what lets `robot_state_publisher` and RViz work in
simulation. Almost every ros2_control setup loads it.

**`JointGroupPositionController`** takes an array of target positions for a
named group of joints and writes them to the command interfaces.

The controllers you will meet most:

| Controller | Takes | Use |
|---|---|---|
| `joint_state_broadcaster` | — | publishes `/joint_states` |
| `position_controllers/JointGroupPositionController` | `Float64MultiArray` | direct angle targets — this lesson |
| `joint_trajectory_controller/JointTrajectoryController` | `JointTrajectory` | timed, interpolated motion — what MoveIt and most arms use |
| `diff_drive_controller/DiffDriveController` | `Twist` on `/cmd_vel` | wheeled bases |
| `velocity_controllers/...`, `effort_controllers/...` | | when you command speed or torque |

> Notice what is **not** in that list: anything for legs. There is no
> `legged_controller`. That gap is exactly what
> [lessons 20–22](20-leg-kinematics.md) fill in by hand.

### `update_rate: 200`

The control loop runs at 200 Hz. The gait node runs at 50 Hz. That is fine and
normal: the controller holds the last command between updates. The control
loop should be at least as fast as the thing commanding it.

---

## Part 3 — sending commands

The one method that differs, from
[`gait_to_controller.py`](../src/spider_bot/spider_bot/gait_to_controller.py):

```python
class GaitToController(GaitController):
    """The same gait, sent to ros2_control as position commands."""

    def __init__(self):
        super().__init__()

        self.declare_parameter(
            'command_topic', '/leg_position_controller/commands')
        topic = self.get_parameter('command_topic').value

        self._command_publisher = self.create_publisher(
            Float64MultiArray, topic, 10)

        # The parent class made a /joint_states publisher we must not use
        # here - joint_state_broadcaster owns that topic now.
        self.destroy_publisher(self._publisher)
        self._publisher = None

    def publish_positions(self, positions):
        msg = Float64MultiArray()
        # The order must match the `joints:` list in the controller YAML.
        msg.data = positions
        self._command_publisher.publish(msg)
```

Everything else — the gait, the kinematics, the `/cmd_vel` handling — is
inherited unchanged. That is only possible because
[`gait_controller.py`](../src/spider_bot/spider_bot/gait_controller.py)
separates `compute_joint_positions()` from `publish_positions()`. Same
principle as the testable node in [lesson 14](14-testing.md): decide in one
place, act in another.

### The array order

`Float64MultiArray` is a bare list of numbers with **no names attached**. The
order must match the `joints:` list in the YAML exactly, or you will command
the front left femur with the rear right tibia's angle — and watch the robot
tie itself in a knot with no error message anywhere.

This repo keeps `LEG_MOUNTS`, the YAML `joints:` list and the URDF in the same
order for exactly this reason. When in doubt:

```bash
ros2 control list_controllers -v         # shows the claimed interfaces, in order
```

---

## Part 4 — loading controllers

Controllers must be loaded after the hardware exists. From the command line:

```bash
ros2 run controller_manager spawner joint_state_broadcaster
ros2 run controller_manager spawner leg_position_controller
```

Or, from a launch file, chained so it cannot race
([lesson 18](18-gazebo-simulation.md)):

```python
    RegisterEventHandler(OnProcessExit(
        target_action=spawn,
        on_exit=[load_joint_state_broadcaster])),
    RegisterEventHandler(OnProcessExit(
        target_action=load_joint_state_broadcaster,
        on_exit=[load_leg_controller])),
```

The `spawner` loads a controller, activates it, and exits — which makes its
exit a convenient signal that the next stage can start.

---

## Try it

```bash
ros2 launch spider_bot gazebo.launch.py
```

Inspect the control stack:

```bash
ros2 control list_controllers
# joint_state_broadcaster  ... active
# leg_position_controller  ... active

ros2 control list_hardware_interfaces
# shows all 12 command interfaces and 24 state interfaces

ros2 topic info /leg_position_controller/commands
ros2 topic hz /joint_states
```

Command the robot by hand — stop the gait node first, or you will fight it:

```bash
ros2 topic pub /leg_position_controller/commands std_msgs/msg/Float64MultiArray \
  "{data: [0.0, 0.2, -1.7,  0.0, 0.2, -1.7,  0.0, 0.2, -1.7,  0.0, 0.2, -1.7]}" --once
```

All four legs move to the same pose. Change one number and watch which joint
responds — that is how you verify the array order empirically.

Switch controllers at runtime:

```bash
ros2 control set_controller_state leg_position_controller inactive
ros2 control set_controller_state leg_position_controller active
```

While it is inactive, commands are ignored. That is the safe way to hand a
robot between two controllers.

---

## Moving to real hardware

The honest summary of what changes:

1. Write a hardware interface plugin (C++, inheriting
   `hardware_interface::SystemInterface`) with `read()`, `write()`,
   `on_init()` and `on_activate()`. `read()` polls your servos; `write()`
   sends them targets.
2. Change the `<plugin>` line in the URDF to yours.
3. Run `ros2_control_node` yourself instead of letting Gazebo host it.
4. Everything else — the YAML, the controllers, your gait node — is
   **unchanged**.

Point 4 is why this layer is worth the ceremony. It is also why you should
develop in simulation: identical code, no smoke.

---

## Common mistakes

**`Controller 'x' not found` / the spawner exits immediately.**
It ran before `controller_manager` existed. Chain it with
`RegisterEventHandler`.

**The robot does not move and nothing errors.**
Check `ros2 control list_controllers` — the controller is probably `inactive`.

**The legs move to nonsense poses.**
The command array order does not match the `joints:` list in the YAML.

**Two nodes publish `/joint_states` and the model jitters.**
In simulation, `joint_state_broadcaster` owns that topic. Your gait node must
publish commands, not states.

**`Failed to load hardware plugin`.**
`gazebo_ros2_control` is not installed, or the plugin name is misspelled.
`sudo apt install ros-humble-gazebo-ros2-control`.

**Commands are accepted but the joint barely moves.**
`effort` in the URDF `<limit>` is too low for the mass, or the joint has too
much `damping`.

**`<parameters>` path not found.**
`$(find spider_bot)` resolves to the *installed* share directory. Rebuild so
the YAML is actually installed.

---

## Recap

- ros2_control sits between your code and the actuators, so the same
  controllers run in simulation and on hardware.
- The URDF `<ros2_control>` block declares the hardware plugin and each
  joint's command/state interfaces.
- The YAML declares which controllers exist and which joints they own.
- `joint_state_broadcaster` publishes `/joint_states`; your node publishes
  *commands*. Never both.
- `Float64MultiArray` has no names — the order is the contract.
- Controllers load after the hardware. Chain the launch actions.

**Next:** [20 — Leg inverse kinematics](20-leg-kinematics.md)
