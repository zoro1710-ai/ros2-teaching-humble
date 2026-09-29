# Demo cheat sheet — the grand finale + the spider

Copy-paste commands for running the end-of-course demo live. Every block is a
separate terminal unless it says otherwise. Ubuntu 22.04 + ROS 2 Humble.

> Source your shell in **every** terminal first:
> ```bash
> source /opt/ros/humble/setup.bash
> source ~/ros2-teaching-humble/install/setup.bash
> ```

---

## 0 — One-time build (after pulling or adding files)

```bash
cd ~/ros2-teaching-humble
colcon build --symlink-install
source install/setup.bash
```

Confirm it worked:

```bash
ros2 pkg executables turtle_capstone
# -> turtle_capstone mission_client
#    turtle_capstone mission_control
ros2 interface show ros2_basics_interfaces/action/CatchMission
```

---

## 1 — The grand finale (nodes + topics + services + params + actions)

**Terminal 1 — world + brain:**

```bash
ros2 launch turtle_capstone grand_finale.launch.py
```

**Terminal 2 — send the goal (the button):**

```bash
ros2 run turtle_capstone mission_client 5      # catch 5 turtles
ros2 run turtle_capstone mission_client 10     # catch 10
```

**Terminal 3 — the four live moments to show:**

```bash
# (a) the graph: 2 nodes, topics between them, /spawn /kill services
rqt_graph

# (b) tune it LIVE while it hunts (parameters, no restart)
ros2 param set /mission_control angular_gain 12.0    # overshoot / orbit
ros2 param set /mission_control angular_gain 1.0     # swings wide
ros2 param set /mission_control linear_gain 4.0      # faster, sloppier
ros2 param get /mission_control linear_gain          # read one back

# (c) inspect the action + topics
ros2 action list
ros2 action info /catch_mission -t
ros2 topic echo /alive_turtles
ros2 topic hz /turtle1/cmd_vel
```

**(d) Cancel a mission mid-hunt (the other half of what makes it an action):**

```bash
ros2 run turtle_capstone mission_client 20
# ...let it catch a few, then press Ctrl-C in THIS terminal.
# The turtle stops; the server logs "mission canceled after N catches".
```

Reset the scene any time by killing Terminal 1 (Ctrl-C) and relaunching.

---

## 2 — The spider glimpse (same /cmd_vel, a walking robot)

**Terminal 1 — model + gait controller + RViz (no simulator needed):**

```bash
ros2 launch spider_bot walk.launch.py
```

In RViz set **Global Options → Fixed Frame = `base_link`** so the legs are easy
to watch.

**Terminal 2 — drive it with the SAME message type the turtle used:**

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"     # walk
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.1}}"     # strafe
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.6}}"    # turn
```

Or drive interactively:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Tune the gait live while it walks:

```bash
ros2 param set /gait_controller cycle_time 0.4      # faster steps
ros2 param set /gait_controller step_height 0.08    # higher leg lift
```

> **Watch the legs, not the body.** `walk.launch.py` has no physics — the body
> stays at the origin and the legs cycle underneath (a treadmill). That is
> correct. The body only travels in Gazebo (`gazebo.launch.py`, lesson 18),
> which needs classic Gazebo installed.
>
> A **zero** Twist (`x=0.0`) makes nothing move — use a non-zero value.

---

## 3 — Stop everything cleanly

```bash
# Ctrl-C in each launch terminal. If something lingers:
pkill -f "[t]urtlesim_node"
pkill -f "[m]ission_control"
pkill -f "[r]obot_state_publisher"
pkill -f "[r]viz2"
```

> The `[t]` bracket trick stops `pkill` from matching (and killing) its own
> command line.

---

## Troubleshooting the demo

| Symptom | Fix |
|---|---|
| `Package 'turtle_capstone' not found` | You didn't `source install/setup.bash` in that terminal. |
| `ros2 run` can't find `mission_control`/`mission_client` | New entry point → `colcon build --symlink-install` then re-source. |
| Spider launch dies: `xacro ... showed stderr output` | A xacro warning is treated as fatal; fix the warning, or set `on_stderr='warn'` on the `Command`. |
| Spider not moving | Twist is all zeros, or you're watching the body (it stays put — watch the legs). |
| `CatchMission` missing after edit to the `.action` | Rebuild interfaces: `colcon build --packages-select ros2_basics_interfaces` then re-source. |
| Turtles spawn with blank names on a re-run | Fixed in `mission_control` (session-wide counter); rebuild if on an old copy. |

**Back to:** [the course index](README.md) · full command reference: [cheatsheet.md](cheatsheet.md)
