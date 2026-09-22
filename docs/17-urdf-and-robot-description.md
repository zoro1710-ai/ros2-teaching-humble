# 17 — URDF: describing a four legged robot

**Goal:** describe a robot's physical shape and joints so that the whole ROS
ecosystem — RViz, TF2, Gazebo, Nav2 — knows what it is looking at.

**Code:** [`spider_bot.urdf.xacro`](../src/spider_bot/urdf/spider_bot.urdf.xacro),
[`display.launch.py`](../src/spider_bot/launch/display.launch.py)

---

## Run it first

```bash
sudo apt install ros-humble-xacro ros-humble-joint-state-publisher-gui
cd ~/ros2_ws && colcon build --packages-select spider_bot && source install/setup.bash

ros2 launch spider_bot display.launch.py
```

RViz opens with a grey body and four orange legs, plus a window of sliders.
Drag them and the legs move. That is a robot description working.

---

## What a URDF actually is

A URDF is an XML file describing **links** (rigid bodies) connected by
**joints**. That is all.

```
base_link
  ├── front_left_coxa ── front_left_femur ── front_left_tibia ── front_left_foot
  ├── front_right_coxa ── ...
  ├── rear_left_coxa ── ...
  └── rear_right_coxa ── ...
```

Four legs × 3 moving joints = **12 joints**, plus 4 fixed foot frames.

Two rules, and they are the same rules as the TF tree in
[lesson 12](12-tf2.md) — because the URDF *is* what generates the TF tree:

1. Every link has exactly one parent. No loops.
2. `base_link` is the root, and the rest of ROS expects that name.

### A link

```xml
<link name="front_left_femur">
  <visual>                      <!-- what you see in RViz -->
    <origin xyz="0.05 0 0" rpy="0 1.5708 0"/>
    <geometry>
      <cylinder radius="0.015" length="0.10"/>
    </geometry>
    <material name="leg_orange"/>
  </visual>
  <collision>                   <!-- what physics bumps into -->
    ...same shape...
  </collision>
  <inertial>                    <!-- mass, for physics -->
    <mass value="0.10"/>
    <inertia ixx="..." ixy="0" ixz="0" iyy="..." iyz="0" izz="..."/>
  </inertial>
</link>
```

- **visual** — RViz only. Can be a mesh (`.dae`/`.stl`) for a pretty robot.
- **collision** — used by Gazebo and collision checkers. Keep it *simple*:
  boxes, cylinders and spheres. A detailed mesh here will make your
  simulation crawl.
- **inertial** — required by Gazebo ([lesson 18](18-gazebo-simulation.md)).
  A link with no mass is ignored or, worse, makes the physics explode.

Note the `<origin>` on the visual. The link's frame is at the *joint*, but a
cylinder is drawn centred on its own middle, so it has to be pushed out by
half its length — and rotated, because a `<cylinder>` points along **z** and
our legs point along **x**. `rpy="0 1.5708 0"` is that 90° pitch.

### A joint

```xml
<joint name="front_left_femur_joint" type="revolute">
  <parent link="front_left_coxa"/>
  <child link="front_left_femur"/>
  <origin xyz="0.05 0 0" rpy="0 0 0"/>
  <axis xyz="0 -1 0"/>
  <limit lower="-1.5708" upper="1.5708" effort="20.0" velocity="6.0"/>
  <dynamics damping="0.05" friction="0.01"/>
</joint>
```

| Field | Meaning |
|---|---|
| `type` | `revolute` (rotates, with limits), `continuous` (rotates forever, like a wheel), `prismatic` (slides), `fixed` (welded) |
| `parent` / `child` | direction matters, exactly like TF |
| `origin` | where the child's frame sits relative to the parent's, **at zero angle** |
| `axis` | which way the joint rotates, in the child frame |
| `limit` | `lower`/`upper` in radians; `effort` in N·m; `velocity` in rad/s |

### The sign convention you must write down

```xml
<axis xyz="0 -1 0"/>
```

Not `0 1 0`. With `-y` as the axis, a **positive** femur angle **lifts** the
foot — which is the convention the kinematics code in
[lesson 20](20-leg-kinematics.md) is written in.

Either choice is valid. What is not valid is choosing one in the model and
the other in the code. Most "my leg bends backwards" bugs are exactly this,
and they take hours because nothing errors — the robot just looks wrong.

Write your convention in a comment, in both files. This repo does.

---

## xacro: not writing the same leg four times

Four legs × ~60 lines of XML = 240 lines of copy-paste, and four places to
edit when a link length changes. `xacro` is XML with macros and maths.

### Properties

```xml
<xacro:property name="femur_length" value="0.10"/>
```

Used as `${femur_length}`, and arithmetic works:

```xml
<origin xyz="${femur_length/2} 0 0" rpy="0 ${pi/2} 0"/>
```

### Macros

```xml
<xacro:macro name="leg" params="name x y yaw">
  <joint name="${name}_coxa_joint" type="revolute">
    <origin xyz="${x} ${y} 0" rpy="0 0 ${yaw}"/>
    ...
</xacro:macro>
```

Then four legs are four lines:

```xml
<xacro:leg name="front_left"  x="0.12"  y="0.08"  yaw="${pi/4}"/>
<xacro:leg name="front_right" x="0.12"  y="-0.08" yaw="${-pi/4}"/>
<xacro:leg name="rear_left"   x="-0.12" y="0.08"  yaw="${3*pi/4}"/>
<xacro:leg name="rear_right"  x="-0.12" y="-0.08" yaw="${-3*pi/4}"/>
```

The `yaw` values splay each leg 45° out from its corner, so every leg's own
`+x` points diagonally away from the body. That is what makes it look like a
spider rather than a table — and, more usefully, it means all four legs use
**identical** kinematics, just rotated.

> Those four yaw values must match `LEG_MOUNTS` in
> [`leg_kinematics.py`](../src/spider_bot/spider_bot/leg_kinematics.py).
> Two sources of truth is a bug waiting to happen; at minimum, cross-reference
> them in comments.

### Seeing the expanded XML

xacro is not magic — it is a preprocessor. Look at what it produces:

```bash
xacro src/spider_bot/urdf/spider_bot.urdf.xacro > /tmp/spider.urdf
wc -l /tmp/spider.urdf
check_urdf /tmp/spider.urdf
```

`check_urdf` (from `liburdfdom-tools`) prints the link tree and catches
structural errors. Run it whenever something looks wrong.

---

## robot_state_publisher: URDF → TF

This is the piece that confuses people, so read it slowly.

```
  /joint_states              robot_state_publisher              /tf
  (sensor_msgs/JointState) ──────────────────────────────────> (TF frames)
  "femur_joint is at 0.3 rad"        + the URDF                 "front_left_femur
                                                                 is HERE in 3D"
```

**`robot_state_publisher` does not decide where the joints are.** It takes
joint *angles* from `/joint_states`, combines them with the URDF's geometry,
and publishes the resulting TF tree. It is pure maths, no policy.

Something else must supply `/joint_states`:

| Who publishes it | When |
|---|---|
| `joint_state_publisher_gui` | this lesson — sliders you drag |
| your gait controller | [lesson 21](21-gait-generation.md) |
| `joint_state_broadcaster` (ros2_control) | [lesson 19](19-ros2-control.md), simulation and real hardware |

Exactly one of them at a time. Two publishers on `/joint_states` makes the
model jitter between two answers — a classic and very confusing bug.

### Loading the URDF in a launch file

From [`display.launch.py`](../src/spider_bot/launch/display.launch.py):

```python
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )
```

Three details, each of which is a common failure:

1. **`Command(['xacro ', urdf_file])`** runs xacro at launch time and
   captures its stdout. Note the **space** after `xacro` — without it you get
   `xacro/path/to/file` and a confusing "command not found".
2. **`value_type=str`** is required. Without it, launch treats the enormous
   XML string as something else and you get a type error, or a parameter
   containing a file path instead of the model.
3. The parameter must be called exactly **`robot_description`**. Everything
   downstream — RViz, `spawn_entity.py`, ros2_control — looks for that name.

---

## Try it

```bash
ros2 launch spider_bot display.launch.py
```

Then explore what it created:

```bash
ros2 topic echo /joint_states --once        # 12 names and 12 positions
ros2 run tf2_tools view_frames              # writes frames.pdf: 17 frames
ros2 run tf2_ros tf2_echo base_link front_left_foot
```

That last command is the link back to [lesson 12](12-tf2.md): the URDF has
given you, for free, the transform from the body to each foot. Drag a slider
and watch the numbers change.

Check the parameter itself:

```bash
ros2 param get /robot_state_publisher robot_description | head -20
```

### Things worth trying

- Set `body_height` in the xacro to `0.12`, rebuild, relaunch. Everything
  scales because nothing was hard-coded twice.
- In RViz, tick the **TF** display and set Marker Scale to `0.1`. Now you can
  see every joint frame and which way its axes point. This is the fastest way
  to check an `<axis>` is what you think it is.
- Change one leg's `<axis>` to `0 1 0`, rebuild, and drag its femur slider.
  It bends the wrong way, with no error at all. Change it back.

---

## Common mistakes

**RViz shows nothing, or "No transform from [x] to [base_link]".**
`/joint_states` has no publisher, so `robot_state_publisher` cannot compute
anything. Start `joint_state_publisher_gui`, or set Fixed Frame to a frame
that does exist.

**"Invalid <axis> ... " or the model looks scrambled.**
An `<origin>` on a joint is relative to the *parent*, and applies at zero
angle. Getting parent/child backwards is the usual cause.

**Everything is in the right place but rotated 90°.**
A `<cylinder>` points along **z**. Legs along **x** need `rpy="0 1.5708 0"`
on the visual and collision origins.

**The model is invisible in Gazebo but fine in RViz.**
You wrote `<visual>` but no `<collision>` and `<inertial>`.

**`xacro: command not found`.**
`sudo apt install ros-humble-xacro`, and check for the space in
`Command(['xacro ', urdf_file])`.

**The joints jitter between two poses.**
Two nodes are publishing `/joint_states`. Pick one.

**A joint moves further than it should.**
`<limit>` is in **radians**, not degrees. `1.5708`, not `90`.

---

## Recap

- URDF = links + joints. It generates the TF tree.
- `<visual>` for looks, `<collision>` kept simple, `<inertial>` required for
  physics.
- xacro gives you properties, maths and macros — write one leg, use it four
  times.
- Decide a sign convention for each `<axis>`, write it down, and make the
  code match.
- `robot_state_publisher` turns `/joint_states` + URDF into `/tf`. Exactly one
  node may publish `/joint_states`.

## Exercise

Add a fifth frame: a `laser` link on top of the body, 5 cm up, attached with a
`fixed` joint. Confirm with `ros2 run tf2_ros tf2_echo base_link laser` that it
is where you expect, then make it visible in RViz.

**Next:** [18 — Simulating it in Gazebo](18-gazebo-simulation.md)
