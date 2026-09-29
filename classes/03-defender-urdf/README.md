# Class 03: our robot in ROS (the Defender URDF)

From today we learn ROS on **our own robot**, the Defender. Its Blender model has been
turned into a URDF: the file that tells ROS what the robot looks like and how it moves.

```bash
colcon build --packages-select defender_description && source install/setup.bash
ros2 launch defender_description display.launch.py
```

Drag the sliders. Everything you see moving is ROS doing maths on the URDF.

---

## 1. What the Defender actually is

It's not a legged robot. It's a **six-wheel rocker-bogie rover**, the suspension NASA uses on Mars rovers,
with a turret on top.

| Part | What it does | In the URDF |
|---|---|---|
| **Rocker** (one per side) | Big arm pivoting on the chassis; the rear wheel hangs off it | `left_rocker_joint` |
| **Bogie** (one per side) | Smaller arm on the front of the rocker; carries the front and middle wheels | `left_bogie_joint` |
| **Differential** | The red bar at the back. It links the two rockers, so when one goes up the other goes down and the body stays level | `differential_joint` (mimic) |
| **6 steering servos** | The gear on top of every wheel fork, so every wheel can turn | `front_left_steer_joint` ... |
| **6 wheels** | Drive | `front_left_wheel_joint` ... (continuous) |
| **Levelling platform** | 3 servos push rods that tilt a plate, keeping the turret level on slopes | `platform_roll_joint`, `platform_pitch_joint`, `platform_servo_*_joint` |
| **Turret** | Stepper motor (28BYJ-48) turns it | `turret_yaw_joint` |
| **Shooter** | Two N20 motors spin flywheels that pinch and launch the dart | `flywheel_left_joint` (+ mimic right) |
| **ZED 2 camera** | Stereo depth camera on the nose | `zed2_camera` (fixed) |

That's 30 links and 29 joints. The tree is drawn at the top of
[`defender.urdf.xacro`](../../src/defender_description/urdf/defender.urdf.xacro).

---

## 2. Look at it like ROS does

With the launch still running, open a second terminal:

```bash
ros2 run tf2_tools view_frames                      # writes frames_<date>.pdf: the whole tree
ros2 run tf2_ros tf2_echo base_link muzzle          # where is the barrel tip right now?
ros2 topic echo /joint_states --once                # what the sliders publish
```

In RViz, tick **TF** in the Displays panel to see every frame as a little set of axes.

**Colours of the axes:** red = x (forward), green = y (left), blue = z (up). This convention is called REP 103.
Check it on the robot: which way does the barrel point? Which side is `left_rocker` on?

---

## 3. Mimic joints: gears in software

Move the **left_rocker** slider. The right rocker moves the opposite way and the red differential bar
tilts. There's no slider for either of them, because they are **mimic** joints:

```xml
<mimic joint="left_rocker_joint" multiplier="-1"/>
```

The real bevel gears force this. The URDF just says so. The two flywheels work the same way:
they always spin in opposite directions, because that's how they pinch the dart.

---

## 4. Where the numbers came from

Nobody typed the joint positions. They were **measured from the Blender model**:

```
Defender_Asembled.blend
        │  blender -b Defender_Asembled.blend --python src/defender_description/tools/blender_export.py
        ▼
meshes/*.stl                      67 meshes, one per link and colour
urdf/defender_generated.xacro     joint positions, sizes, inertia, colours
        │  included by
        ▼
urdf/defender.urdf.xacro          hand-written: links, joints, axes, limits, masses
```

Changed the CAD? Run the export again and the URDF follows.
Moved a part to a different link? Edit the tables at the top of
[`blender_export.py`](../../src/defender_description/tools/blender_export.py).

Things the exporter had to deal with, which are good to know about any CAD model:

- **Units.** Blender said metres, but the model is really in millimetres. ROS always wants metres.
- **Axes.** The model faces −X. ROS wants +X forward, so everything is turned 180° about Z.
- **Mirrored parts.** Each left/right pair (rockers, wheels...) was ONE mesh. The script cuts them
  down the middle so each side can move on its own.
- **Too many triangles.** The CAD has ~1.5 million triangles, and RViz would crawl. The script simplifies
  them to ~94k (4.7 MB), giving more triangles to the big parts.
- **Pivots.** The rocker and bogie hinge points came from fitting circles to the bearing holes in the mesh.

### What is NOT exact (yet)
| What | Why | How to fix |
|---|---|---|
| Masses | Guessed | Weigh the parts, edit the top of `defender.urdf.xacro` |
| Inertia | Treats each part as a solid box | Good enough for simulation, for now |
| Platform push-rods | The real platform is a closed loop (servo → rod → plate); URDF can only do trees | The rods ride on the servo arms; exact only at zero |
| Differential ratio (0.256) | Estimated from gear sizes | Count the real teeth |
| Rear wheels | The CAD has them 1.75 mm off-centre | Fix the CAD, re-export |

---

## 5. Exercises

1. **Ground clearance.** Use `tf2_echo base_footprint base_link`. How high is the chassis?
   Now move the left rocker to its limit. Does `base_link` move? Why not? *(Hint: which link is the root?)*
2. **Where is the gun pointing?** Set `turret_yaw_joint` to 90°. Use `tf2_echo base_link muzzle`
   and explain the numbers.
3. **Crab walk.** Set all six steering sliders to the same angle. In which direction would the robot drive?
   Now try the front wheels +30° and the rear wheels −30°. What does that do?
4. **Break the tree.** In a copy of the xacro, give `left_bogie` a second parent. Run
   `xacro ... > /tmp/d.urdf && check_urdf /tmp/d.urdf`. Read the error.
5. **Weigh it.** Change the masses to your real measurements, rebuild and relaunch.
   On the RobotModel display in RViz, tick *Mass Properties → Mass* to see each link's
   centre of mass. Which link dominates?
6. **Add a sensor.** The real robot will have an IMU in the chassis. Add an `imu_link`, fixed to
   `base_link`, 3 cm above its origin. Check it in RViz.

---

## Where this goes next

| Next | Uses the URDF for |
|---|---|
| Gazebo simulation | Physics: drive the rover over bumps before building it |
| ros2_control | 6 wheel motors + 6 steering servos behind one standard interface |
| mcu_bridge ([class 02](../02-sensor-motor-boilerplate/README.md)) | Real motors and sensors |
| Platform IK | Roll/pitch wanted → 3 servo angles (like leg IK in [lesson 20](../../docs/20-leg-kinematics.md)) |
| Turret aiming | Camera sees a target → TF says where it is from `muzzle` → turn the turret |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Robot is invisible, RViz says *No transform* | Is `robot_state_publisher` running? Fixed Frame should be `base_footprint` |
| Robot is white or has no meshes | Rebuild and `source install/setup.bash`, so the `meshes/` folder is installed |
| `Could not find package defender_description` | Same: build, then source, in *every* terminal |
| Robot looks 1000× too big | You exported from the CAD without the `MM` scale (don't edit the script's units) |
