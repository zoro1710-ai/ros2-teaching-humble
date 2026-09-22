# 20 — Leg inverse kinematics

**Goal:** given where you want the foot, work out the three joint angles that
put it there.

**Code:** [`leg_kinematics.py`](../src/spider_bot/spider_bot/leg_kinematics.py),
[`test_leg_kinematics.py`](../src/spider_bot/test/test_leg_kinematics.py)

---

## The question

A gait thinks in terms of **feet**: *"put this foot 3 cm further forward and
4 cm off the ground."*

A motor thinks in terms of **angles**: *"femur to 0.31 rad."*

Inverse kinematics is the translation between the two. It is the piece
without which a legged robot is just an expensive sculpture.

No ROS is involved. This module imports `math` and nothing else — which means
you can run it, poke it, and unit test it in milliseconds:

```bash
python3 -c "
from spider_bot.leg_kinematics import GEOMETRY, inverse_kinematics
print(inverse_kinematics(GEOMETRY, 0.16, 0.0, -0.12))"
```

Keeping the maths out of the node is the same discipline as
[lesson 14](14-testing.md). It is worth even more here, because kinematics is
where the subtle bugs live.

---

## Set up the frame first

Half of all IK bugs are a convention nobody wrote down. So, written down:

Each leg has its own frame, with the origin **at the coxa joint**:

```
        +z  up
         │
         │        +x  outward, away from the body
         │      ╱
         │    ╱
         └──────────  +y  left of that
```

A foot on the ground is at **negative z**.

And the joint angles:

| Joint | Axis | Positive means |
|---|---|---|
| coxa | `+z` | swing the leg toward `+y` |
| femur | `-y` | **lift** the foot |
| tibia | `-y` | **lift** the foot, measured relative to the femur (0 = straight) |

The URDF uses `<axis xyz="0 -1 0"/>` for femur and tibia *precisely so that
this is true*. Model and maths must agree; see
[lesson 17](17-urdf-and-robot-description.md).

```python
GEOMETRY = LegGeometry(coxa=0.05, femur=0.10, tibia=0.14)
```

Those are metres, joint centre to joint centre, and they must match the xacro.

---

## Forward kinematics first

Always write FK, even when you only need IK. It is easy, and it gives you a
way to *check* the hard one.

```python
def forward_kinematics(geometry, coxa_angle, femur_angle, tibia_angle):
    """Return the foot position (x, y, z) in the leg frame for three angles."""
    # Work in the vertical plane the leg lies in, then rotate that plane by
    # the coxa angle. `radius` is the distance from the coxa axis.
    radius = (geometry.coxa
              + geometry.femur * math.cos(femur_angle)
              + geometry.tibia * math.cos(femur_angle + tibia_angle))

    z = (geometry.femur * math.sin(femur_angle)
         + geometry.tibia * math.sin(femur_angle + tibia_angle))

    x = radius * math.cos(coxa_angle)
    y = radius * math.sin(coxa_angle)
    return (x, y, z)
```

The insight that makes a 3-DOF leg tractable: **the coxa just rotates a
plane.** Everything below it is a flat, two-link problem in that plane. So:

1. Work out the answer in the plane, giving a radius and a height.
2. Rotate that radius into 3D with the coxa angle.

Note `femur_angle + tibia_angle` in the second term. The tibia angle is
measured *relative to the femur*, so its absolute angle is the sum. Getting
this wrong gives a leg that looks almost right, which is worse than obviously
wrong.

---

## Inverse kinematics

```python
def inverse_kinematics(geometry, x, y, z):
    # 1. The coxa simply points the leg's vertical plane at the target.
    coxa_angle = math.atan2(y, x)

    # 2. Reduce to a 2-link planar problem in that plane.
    radius = math.hypot(x, y)
    planar_x = radius - geometry.coxa        # distance from the femur joint
    reach = math.hypot(planar_x, z)          # straight-line distance to the foot

    longest = geometry.femur + geometry.tibia
    shortest = abs(geometry.femur - geometry.tibia)

    if reach > longest + 1e-9:
        raise LegUnreachable(...)
    if reach < shortest - 1e-9:
        raise LegUnreachable(...)

    # 3. The law of cosines gives the knee angle.
    cos_tibia = ((reach * reach - geometry.femur ** 2 - geometry.tibia ** 2)
                 / (2.0 * geometry.femur * geometry.tibia))
    cos_tibia = max(-1.0, min(1.0, cos_tibia))
    tibia_angle = -math.acos(cos_tibia)

    # 4. "Point at the foot", corrected for the bent knee.
    femur_angle = (math.atan2(z, planar_x)
                   - math.atan2(geometry.tibia * math.sin(tibia_angle),
                                geometry.femur + geometry.tibia * math.cos(tibia_angle)))

    return (coxa_angle, femur_angle, tibia_angle)
```

### Step 1 — the coxa

`atan2(y, x)` is the bearing to the target. That is the entire coxa
calculation. Use `atan2`, never `atan(y/x)`: `atan2` knows which quadrant you
are in and does not divide by zero.

### Step 2 — reduce to two links

Subtract the coxa length and you have a classic two-link arm: a femur and a
tibia, trying to reach a point `reach` away.

### Step 3 — the law of cosines

The triangle is femur, tibia, and the straight line to the foot. The law of
cosines gives the angle between the two links:

```
reach² = femur² + tibia² − 2·femur·tibia·cos(interior angle)
```

Rearranged for `cos`, that is the code above.

**Two details that are not optional:**

**The clamp.**
```python
cos_tibia = max(-1.0, min(1.0, cos_tibia))
```
Floating point will hand you `1.0000000002` for a perfectly reachable point,
and `math.acos` raises `ValueError` on it. In a 50 Hz control loop that kills
your robot mid-stride. Clamp.

**The minus sign.**
```python
tibia_angle = -math.acos(cos_tibia)
```
There are always **two** solutions: knee up and knee down. `acos` returns only
the positive one. We negate to get knee-down, which is what a spider leg looks
like. Flip the sign for the other solution.

A robot that flips between the two solutions mid-stride will snap its leg
through the body. Pick one branch and stay on it.

### Step 4 — the femur

```python
femur_angle = atan2(z, planar_x) − atan2(tibia·sin(θ3), femur + tibia·cos(θ3))
```

Two terms: *"point the whole leg at the foot"*, minus *"the correction for
the fact that the knee is bent"*. If the knee were straight (θ3 = 0) the
second term would be zero.

---

## Unreachable is a normal event

```python
    if reach > longest + 1e-9:
        raise LegUnreachable(
            'foot at (%.3f, %.3f, %.3f) is %.3f m from the femur joint, '
            'but the leg only reaches %.3f m' % (x, y, z, reach, longest))
```

Every time you increase stride length or lower the body, some foot target
leaves the workspace. This is not exotic — it happens on the first afternoon
of gait tuning.

There are **two** limits, and beginners only ever check the first:

- **too far** — `reach > femur + tibia`. Obvious.
- **too close** — `reach < |femur − tibia|`. The leg cannot fold tightly
  enough. With a 0.10 m femur and a 0.14 m tibia, nothing within 0.04 m of the
  femur joint is reachable.

And the caller must handle it. From
[`gait_controller.py`](../src/spider_bot/spider_bot/gait_controller.py):

```python
            try:
                coxa, femur, tibia = inverse_kinematics(GEOMETRY, leg_x, leg_y, leg_z)
            except LegUnreachable as exc:
                # Never let a geometry error kill the control loop. Hold the
                # leg still this tick and tell the operator to slow down.
                self.get_logger().warn(
                    '%s cannot reach its target: %s' % (mount.name, exc),
                    throttle_duration_sec=2.0)
                coxa, femur, tibia = self.neutral_angles(mount)
```

An uncaught exception in a 50 Hz timer callback stops the timer. On a real
robot, that means the legs freeze wherever they happen to be, and it falls
over. Degrade; do not die.

---

## Body frame → leg frame

The gait thinks in **body** coordinates; IK works in **leg** coordinates. The
bridge:

```python
def body_to_leg(mount, x, y, z):
    # Translate so the coxa joint is the origin.
    dx = x - mount.x
    dy = y - mount.y

    # Rotate by -yaw to undo the leg's mounting angle.
    cos_yaw = math.cos(-mount.yaw)
    sin_yaw = math.sin(-mount.yaw)

    leg_x = dx * cos_yaw - dy * sin_yaw
    leg_y = dx * sin_yaw + dy * cos_yaw
    return (leg_x, leg_y, z)
```

This is exactly what TF2 ([lesson 12](12-tf2.md)) would do for you. Doing it
by hand once is worth it, because it makes obvious what a transform *is*: a
translation and a rotation, nothing more.

(In production you would often let TF2 do it, and get timestamping and
interpolation for free. At 50 Hz with a fixed mount, hand-rolling it is
faster and simpler.)

The four mounts:

```python
LEG_MOUNTS = [
    LegMount('front_left', x=0.12, y=0.08, yaw=math.radians(45.0)),
    LegMount('front_right', x=0.12, y=-0.08, yaw=math.radians(-45.0)),
    LegMount('rear_left', x=-0.12, y=0.08, yaw=math.radians(135.0)),
    LegMount('rear_right', x=-0.12, y=-0.08, yaw=math.radians(-135.0)),
]
```

Because every leg is splayed 45° out from its corner, **all four legs use
identical kinematics**. Only the mount transform differs. That is a deliberate
design choice, and it is why there is one `inverse_kinematics` function
instead of four.

---

## Testing it: FK and IK check each other

This is the technique worth stealing from this lesson.

```python
@pytest.mark.parametrize('point', REACHABLE_POINTS)
def test_ik_then_fk_returns_the_same_point(point):
    """IK and FK must be exact inverses for any reachable foot position."""
    angles = inverse_kinematics(GEOMETRY, *point)
    recovered = forward_kinematics(GEOMETRY, *angles)

    for expected, actual in zip(point, recovered):
        assert actual == pytest.approx(expected, abs=1e-9)
```

You do not need to know the right answer. You only need the two functions to
disagree with each other, and the test finds it. Round-tripping catches sign
errors, swapped links, and degree/radian mix-ups instantly.

The reverse direction is also tested — with one caveat worth understanding:

```python
def test_fk_then_ik_returns_the_same_angles(angles):
    """FK then IK recovers the angles, for the knee-down branch.

    Only knee-down (a negative tibia angle) round-trips, because IK always
    picks that solution. That is a deliberate choice, not a bug.
    """
```

And the test that matters most for the robot actually working:

```python
def test_every_neutral_stance_is_reachable():
    """If this fails, the robot cannot even stand up, and every gait built
    on top of it is doomed."""
```

Run them:

```bash
pytest src/spider_bot/test/test_leg_kinematics.py -v
# 18 passed
```

They run in about a second, with no ROS, no build and no simulator.

---

## Try it

```bash
cd ~/ros2_ws
python3 -c "
from spider_bot.leg_kinematics import *
import math

# The neutral standing pose
a = inverse_kinematics(GEOMETRY, 0.16, 0.0, -0.12)
print('neutral:', [round(math.degrees(v), 1) for v in a])

# Foot 4 cm further out
a = inverse_kinematics(GEOMETRY, 0.20, 0.0, -0.12)
print('extended:', [round(math.degrees(v), 1) for v in a])

# Foot swung 30 degrees to the side
a = inverse_kinematics(GEOMETRY, 0.14, 0.08, -0.12)
print('to the side:', [round(math.degrees(v), 1) for v in a])
"
```

Then find the edge of the workspace yourself:

```bash
python3 -c "
from spider_bot.leg_kinematics import *
for r in [0.10, 0.15, 0.20, 0.25, 0.29, 0.30]:
    try:
        inverse_kinematics(GEOMETRY, r, 0.0, -0.12)
        print(r, 'reachable')
    except LegUnreachable as e:
        print(r, 'UNREACHABLE')
"
```

Knowing where that boundary is, for your own geometry, is what keeps a gait
out of trouble.

---

## Common mistakes

**`math domain error` from `acos`.**
You did not clamp the cosine to [−1, 1]. Floating point will get you.

**The leg bends the wrong way.**
Either the `<axis>` in the URDF disagrees with your convention, or you took
`+acos` instead of `−acos`.

**The leg snaps through the body mid-stride.**
The solver is switching between the knee-up and knee-down branches. Pin the
branch.

**Everything is 57× too big or small.**
Degrees somewhere, radians elsewhere. All ROS angles are radians. Use
`math.radians()` at the boundary and nowhere else.

**IK works in a test and fails in the gait.**
You forgot `body_to_leg`, and passed body coordinates into a function
expecting leg coordinates.

**An exception in the control loop stops the robot dead.**
Catch `LegUnreachable`. Degrade to a safe pose and warn.

**The model and the code disagree about link lengths.**
`GEOMETRY` and the xacro properties are two sources of truth. Keep them
together, or at least cross-reference them in comments — this repo does both.

---

## Recap

- IK turns a foot position into joint angles; it is the core of any legged
  robot.
- Keep it in plain Python — no ROS — so it is fast to test.
- The coxa rotates a plane; below it, it is a two-link planar problem solved
  with `atan2` and the law of cosines.
- Always clamp before `acos`, and always pick one solution branch.
- Unreachable targets are normal. Raise a clear error, and have the caller
  degrade safely.
- Write forward kinematics too, and let the two check each other in tests.

**Next:** [21 — Gait generation](21-gait-generation.md)
