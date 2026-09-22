# 21 — Gait generation

**Goal:** coordinate four legs so the robot actually walks.

**Code:** [`gait_controller.py`](../src/spider_bot/spider_bot/gait_controller.py),
[`walk.launch.py`](../src/spider_bot/launch/walk.launch.py),
[`gait.yaml`](../src/spider_bot/config/gait.yaml)

---

## Run it first

No simulator needed:

```bash
ros2 launch spider_bot walk.launch.py
```

Then in another terminal:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
```

The legs start cycling. The body stays at the origin and the legs move
underneath it — a treadmill. For tuning a gait that is exactly what you want:
no falling over, no contact forces, no simulator fighting you. Physics comes
back in [lesson 18](18-gazebo-simulation.md).

---

## What a gait is

A gait is a rule for **when each foot is on the ground**.

Every leg repeats the same cycle, just offset in time:

```
stance   foot planted, sliding backwards relative to the body
         ← this is what actually moves the robot
swing    foot lifted and carried forwards again
         ← this is just resetting
```

Three numbers define it:

| Parameter | Meaning | Here |
|---|---|---|
| `cycle_time` | seconds for one full cycle | 0.8 s |
| `duty_factor` | fraction of the cycle in stance | 0.5 |
| phase offsets | when each leg starts its cycle | see below |

And the offsets are what name the gait:

```python
TROT_PHASES = {
    'front_left': 0.0,
    'rear_right': 0.0,
    'front_right': 0.5,
    'rear_left': 0.5,
}
```

**Diagonal pairs move together.** That is a trot. With `duty_factor = 0.5`,
exactly two legs are down at any moment — always a diagonal pair, so the
support line passes under the centre of mass.

The common four-legged gaits:

| Gait | Duty | Feet down | Character |
|---|---|---|---|
| **crawl / walk** | 0.75 | 3 | slow, very stable — never falls even if you stop mid-step |
| **trot** | 0.5 | 2 (diagonal) | the default. Fast, stable enough, simple |
| **pace** | 0.5 | 2 (same side) | rocks side to side; camels do it |
| **bound / gallop** | < 0.5 | 0–2 | flight phases. Needs real balance control |

Start with a crawl if your robot is heavy or your servos are slow. Trot is the
sweet spot for most hobby robots, and it is what this code does.

> A "tripod gait" is the six-legged equivalent — three legs down at a time.
> With four legs you cannot do that, which is why a quadruped trots.

---

## The foot trajectory

For each leg, each tick, the question is: *where should this foot be?*

```python
    def foot_target(self, mount, phase):
        """Return this foot's target position (x, y, z) in the body frame."""
        neutral_x, neutral_y, neutral_z = self._neutral[mount.name]

        if self.is_stopped():
            return (neutral_x, neutral_y, neutral_z)

        vx, vy = self.foot_velocity(neutral_x, neutral_y)

        # How far the foot travels during one stance phase.
        stance_time = self._cycle_time * self._duty
        stride_x = vx * stance_time
        stride_y = vy * stance_time

        if phase < self._duty:
            # Stance: on the ground, sliding from +half a stride to -half.
            progress = phase / self._duty
            offset_x = stride_x * (0.5 - progress)
            offset_y = stride_y * (0.5 - progress)
            lift = 0.0
        else:
            # Swing: in the air, carried from -half a stride back to +half.
            progress = (phase - self._duty) / (1.0 - self._duty)
            offset_x = stride_x * (progress - 0.5)
            offset_y = stride_y * (progress - 0.5)
            lift = self._step_height * math.sin(math.pi * progress)

        return (neutral_x + offset_x, neutral_y + offset_y, neutral_z + lift)
```

Read the two branches:

**Stance** — the foot starts half a stride *ahead* of neutral and slides to
half a stride *behind*. `lift = 0`, so it stays on the ground. Since the foot
is planted, sliding it backwards in body coordinates is what pushes the body
forwards. This is where all locomotion comes from.

**Swing** — the reverse, in the air, with a lift.

```python
lift = self._step_height * math.sin(math.pi * progress)
```

A half sine: zero at lift-off, maximum in the middle, zero at touch-down.
Smooth at both ends, which matters — a triangular profile means the foot
slams down at full vertical speed, and on real hardware that is how you
destroy gearboxes.

### Stride length is derived, not set

```python
stride = foot_velocity × stance_time
```

You do not tune stride length directly. It falls out of how fast you asked
the robot to go and how long the foot is on the ground. Go faster, and the
strides get longer — until a foot leaves the workspace, which is what
`LegUnreachable` is for ([lesson 20](20-leg-kinematics.md)).

---

## Turning

This is the part people usually get wrong. A `Twist` has an angular component,
and for a legged robot that is not a special case — it is the same maths.

```python
    def foot_velocity(self, neutral_x, neutral_y):
        """Return how fast this foot must travel over the ground, in body frame.

        A foot planted on the ground has to cancel the body's motion. For a
        pure translation every foot moves at -v. Add a rotation and each foot
        also has to sweep around the turning centre:

            v_point = v_body + omega x r

        In 2D, omega x r is (-omega * ry, omega * rx).
        """
        vx = self._vx - self._wz * neutral_y
        vy = self._vy + self._wz * neutral_x
        return (vx, vy)
```

`v = v_body + ω × r` is the rigid-body velocity formula, and `r` here is the
foot's neutral position in the body frame.

The consequence: during a turn, the **outer legs take longer strides than the
inner ones**, automatically, because their `r` is larger. You do not write a
special case for turning. Two lines of cross product and it is handled.

Translation and rotation combine freely, which is what makes the node a valid
`/cmd_vel` consumer — see [lesson 22](22-navigation-for-legged-robots.md).

---

## The control loop

```python
    def compute_joint_positions(self):
        """Advance the gait one tick and return the twelve joint angles."""
        if not self.is_stopped():
            self._phase = (self._phase + self._period / self._cycle_time) % 1.0

        positions = []

        for mount in LEG_MOUNTS:
            leg_phase = (self._phase + TROT_PHASES[mount.name]) % 1.0

            body_x, body_y, body_z = self.foot_target(mount, leg_phase)
            leg_x, leg_y, leg_z = body_to_leg(mount, body_x, body_y, body_z)

            try:
                coxa, femur, tibia = inverse_kinematics(GEOMETRY, leg_x, leg_y, leg_z)
            except LegUnreachable as exc:
                self.get_logger().warn(
                    '%s cannot reach its target: %s' % (mount.name, exc),
                    throttle_duration_sec=2.0)
                coxa, femur, tibia = self.neutral_angles(mount)

            positions.extend([coxa, femur, tibia])

        return positions
```

Five steps per leg, per tick: **phase → foot target in body frame → leg frame
→ IK → angles.** That is the whole architecture of a legged robot's low level.

Design choices worth copying:

**The `/cmd_vel` callback does nothing but store.**

```python
    def on_cmd_vel(self, msg):
        self._vx = self.clamp(msg.linear.x, self._max_linear)
        self._vy = self.clamp(msg.linear.y, self._max_linear)
        self._wz = self.clamp(msg.angular.z, self._max_angular)
```

All the work happens on a fixed-rate timer. If the gait ran in the `/cmd_vel`
callback, its speed would depend on how often commands arrived — and a
dropped message would freeze the robot mid-stride. Sensor in, timer computes.
Same pattern as the capstone controller in [lesson 16](16-capstone-catch-them-all.md).

**Commands are clamped, not trusted.** Nav2 will happily ask for 0.5 m/s. A
robot that cannot do it should walk at its maximum, not tear a leg off trying.

**The phase freezes when stopped.** So the robot always starts walking from
the same pose, rather than from wherever it happened to stop.

**Unreachable degrades, it does not crash.** An uncaught exception in a timer
callback kills the timer, and the robot freezes mid-stride.

---

## Tuning

Every number lives in
[`gait.yaml`](../src/spider_bot/config/gait.yaml), so you can change it while
the robot walks ([lesson 07](07-parameters.md)):

```bash
ros2 param set /gait_controller cycle_time 0.4        # quicker steps
ros2 param set /gait_controller step_height 0.08      # higher lift
ros2 param set /gait_controller body_height 0.16      # stand taller
```

What each one does, and where it bites:

| Parameter | Increase it | Too far and... |
|---|---|---|
| `cycle_time` | slower, longer steps | the robot rocks and loses balance between footfalls |
| `duty_factor` | more feet down, more stable | less time to swing — the foot has to move fast |
| `step_height` | clears bigger obstacles | wasted energy; foot slams down |
| `body_height` | more ground clearance | legs approach full extension, losing force and workspace |
| `stance_radius` | wider, more stable footprint | legs approach the edge of the workspace |
| `max_linear_speed` | faster | strides grow until IK fails |

The single most common beginner mistake: **making `max_linear_speed` large**.
Stride length is proportional to it, so the feet reach further and further
out until `LegUnreachable` fires every tick and the robot shuffles in place.
If you see that warning, slow down or shorten `cycle_time`.

---

## Try it

```bash
ros2 launch spider_bot walk.launch.py
```

Drive it properly:

```bash
sudo apt install ros-humble-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Or one command at a time, which is better for watching one behaviour:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"     # forward
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.1}}"     # sideways
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.6}}"    # spin
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.1}, angular: {z: 0.4}}"                              # arc
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}"                     # stop
```

Sideways is worth pausing on: the gait handles strafing with no extra code,
because the stride is a *vector*. Wheeled differential-drive robots cannot do
that at all.

Watch what it produces:

```bash
ros2 topic echo /joint_states
ros2 topic hz /joint_states                 # should be ~50
ros2 run rqt_plot rqt_plot /joint_states/position[1]    # front_left_femur
```

`rqt_plot` on one joint is the fastest way to *see* the gait: a smooth
periodic curve, with the swing phase visibly different from stance.

### Experiments

1. `ros2 param set /gait_controller duty_factor 0.75` — a crawl. Three feet
   down. Noticeably more stable, noticeably slower.
2. Set `max_linear_speed` to `0.5` and command `0.5`. Watch the
   `LegUnreachable` warnings and the robot shuffle. Now you know that failure.
3. Set `step_height` to `0.0`. The feet drag through the whole cycle — no
   swing, no progress.
4. Set `cycle_time` to `0.2`. The gait is frantic; on real hardware the servos
   could not keep up.

---

## Testing a gait

The gait tests in
[`test_gait_controller.py`](../src/spider_bot/test/test_gait_controller.py)
answer questions a simulator would take minutes to answer:

```python
@pytest.mark.parametrize('command', [
    {'vx': 0.15},                    # full speed ahead
    {'wz': 0.8},                     # spin on the spot
    {'vx': 0.15, 'wz': 0.8},         # the worst case: both at once
    ...
])
def test_no_leg_goes_out_of_reach_at_any_phase(node, command):
    """Every foot target, through a whole cycle, must be reachable."""
```

That test walks the gait through a full cycle at every commanded extreme and
asserts nothing leaves the workspace. Combined with
`test_joint_limits_are_respected`, it means: **if the tests pass, this robot
can physically execute every command it accepts.**

That is a much stronger guarantee than "it looked fine in RViz", and it takes
two seconds.

---

## What this gait does not do

Be clear about the ceiling here. This is an **open-loop** gait: it plays the
same pattern regardless of what the world does.

It has no idea whether a foot actually touched the ground, whether the body is
tilting, or whether it is about to fall. On flat ground with decent servos,
that is enough — and it is how a great many hobby quadrupeds work.

To go further you need feedback:

| Next capability | What it needs |
|---|---|
| don't fall on uneven ground | IMU + body attitude control (tilt the body to keep it level) |
| know when a foot lands | contact sensors or current sensing, plus early touch-down handling |
| step over obstacles | foothold planning from an elevation map |
| recover from a push | a balance controller, e.g. capture point or MPC |
| run | flight phases, and a whole-body controller |

Each is a serious project. Open-loop trot first, though — everything else
builds on a leg controller that works.

---

## Common mistakes

**The robot shuffles and logs `LegUnreachable` constantly.**
The commanded speed is too high for the cycle time. Lower
`max_linear_speed` or `cycle_time`.

**The legs move but in simulation nothing happens.**
Friction on the feet ([lesson 18](18-gazebo-simulation.md)), or you are
publishing `/joint_states` instead of commands
([lesson 19](19-ros2-control.md)).

**The robot walks backwards.**
A sign flipped in the stance branch, or the leg mount yaw values disagree
between the URDF and `LEG_MOUNTS`.

**Motion is jerky.**
`update_rate` is too low, or `step_height` uses a linear profile instead of
the sine.

**It works forwards but not turning.**
The `ω × r` term is missing or has the wrong sign. Check
`foot_velocity`.

**The gait speed depends on how fast `/cmd_vel` arrives.**
You put the gait in the subscription callback. Move it to a timer.

**The robot lurches when it starts.**
The phase was not reset, so it starts mid-swing.

---

## Recap

- A gait is a schedule of which feet are down when: `cycle_time`,
  `duty_factor`, and phase offsets.
- Trot = diagonal pairs, duty 0.5. Crawl = duty 0.75, much more stable.
- Stance moves the robot; swing just resets the foot. Lift with a half sine.
- Stride length is derived from commanded velocity × stance time — not tuned
  directly.
- Turning is `v = v_body + ω × r`. No special case.
- Per tick, per leg: phase → body-frame target → leg frame → IK → angles.
- Clamp commands, degrade on unreachable, and run on a fixed-rate timer.

**Next:** [22 — Navigation for legged robots](22-navigation-for-legged-robots.md)
