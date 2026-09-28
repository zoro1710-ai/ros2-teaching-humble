# 23 — Grand finale: every concept at once, and where it goes in the real world

**Goal:** after teaching nodes, topics, services, parameters and actions one at
a time, show all five working together in a single running system — then draw
the straight line from this toy to real robots (rovers, drones, arms), and end
with a glimpse of the walking robot.

This is the lesson you run *live* at the end of a course. It is built so that
one command starts it and one command drives it. For a bare list of the commands
to copy-paste while presenting, see the
[demo cheat sheet](demo-cheatsheet.md).

**Code:**
[`mission_control.py`](../src/turtle_capstone/turtle_capstone/mission_control.py),
[`mission_client.py`](../src/turtle_capstone/turtle_capstone/mission_client.py),
[`grand_finale.launch.py`](../src/turtle_capstone/launch/grand_finale.launch.py),
[`grand_finale.yaml`](../src/turtle_capstone/config/grand_finale.yaml),
[`CatchMission.action`](../src/ros2_basics_interfaces/action/CatchMission.action)

---

## 1 — Why did we learn all that? (the real-world map)

The single most useful thing you can tell a class at the end is this:

> A real rover, drone or robot arm is **the same five pieces** you just learned,
> with better maths in the middle.

Put this table up and walk down it. The left column is what they just did in
turtlesim; the right column is the same primitive on real hardware.

| Concept | In turtlesim you did… | On a rover / drone / arm it becomes… |
|---|---|---|
| **Nodes** | one process per job | camera driver, motor driver, planner, localizer — each its own node |
| **Topics** | `/turtle1/pose`, `/cmd_vel` | wheel odometry, IMU, LiDAR scans, and `/cmd_vel` to the motor controller |
| **Services** | `/spawn`, `/kill` | "take a photo", "home the arm", "reset odometry" — one request, one answer |
| **Parameters** | `linear_gain`, `catch_distance` | wheel radius, PID gains, camera calibration — tuned per robot, no recompile |
| **Actions** | "catch N turtles" | "drive to waypoint", "pick up the sample", "scan this area" — long jobs with feedback and cancel |

The choice between them is the real skill, and it is the same on any robot:

- **Is it a continuous stream many nodes might want?** → topic (sensor data, `/cmd_vel`).
- **Is it a quick request with one answer?** → service (reset, configure, query).
- **Is it a long job you want to watch and be able to abort?** → action (navigation, manipulation).
- **Is it a number you want to tune without recompiling?** → parameter.
- **Is it a distinct job that should fail on its own?** → its own node.

A Mars-style rover is literally this: topics carry the camera and IMU streams, a
service triggers a drill sample, an **action** drives it to a target rock with
progress feedback and the ability to cancel if the battery drops, and every gain
and limit is a parameter. Nothing new — just harder maths inside the control
loop.

---

## 2 — The combined show: one action goal runs everything

The capstone in [lesson 16](16-capstone-catch-them-all.md) already combined
nodes, topics, services and parameters. It deliberately left **actions** out.
This finale folds them in: the *entire* mission is one action.

You send one goal — "catch 5 turtles" — and a single node autonomously spawns
them, hunts each one down with a P-controller, and reports progress the whole
time. You can retune it mid-hunt and cancel it mid-hunt.

```
   you ──(action goal: "catch 5 turtles")──▶  mission_control  (ACTION server)
                                              │   ├─ PARAMS: linear_gain, angular_gain,
                                              │   │          catch_distance  (live-tunable)
        ◀──(feedback: caught 2/5, 1.3 m)─────┤   ├─ SERVICE calls: /spawn, /kill  (turtlesim)
        ◀──(result: 5 caught in 12.4 s)──────┘   ├─ TOPICS: publishes /turtle1/cmd_vel,
                                                  │          /alive_turtles;
                                                  │          subscribes /turtle1/pose
                                                  └─ NODES: this one + turtlesim
   ...press Ctrl-C on the client mid-hunt  →  the turtle stops cleanly, and the
                                              result reports how many it managed
```

All five concepts, in one node graph, on screen at once.

### The one detail worth explaining

An action server that runs a control loop has a problem: while its
`execute_callback` is looping, *who* answers the pose subscription and the
`/spawn` and `/kill` service replies it is waiting on? The answer is
[lesson 11](11-executors-and-callback-groups.md) doing real work: a
`ReentrantCallbackGroup` on a `MultiThreadedExecutor`. That lets the pose
callback, the service futures and the long-running mission callback all make
progress on different threads at the same time. That is exactly the pattern a
real navigation action server uses.

---

## 3 — Run it

Two terminals. **Terminal 1** starts the world and the brain:

```bash
ros2 launch turtle_capstone grand_finale.launch.py
```

**Terminal 2** is the button you press:

```bash
ros2 run turtle_capstone mission_client 5     # catch 5 turtles
```

Watch the feedback stream in terminal 2 while the turtle hunts in the window.
When it finishes it prints, e.g., `MISSION OVER: 5 caught in 11.3 s`.

---

## 4 — Presenter script (what to say while it runs)

Do these in order; each one demonstrates a different concept *live*.

1. **Show the graph.** In a third terminal:
   ```bash
   rqt_graph
   ```
   Point at it: "two **nodes**, connected by **topics**; the arrows into
   turtlesim are the `/spawn` and `/kill` **services**." One picture, three
   concepts.

2. **Prove it is an action, not a service.** Send the goal, and narrate the
   feedback lines as they scroll: "a service would give me *one* answer at the
   end. This is **feedback** — progress, every tick, while the job runs."

3. **Tune it live** (this is the parameters payoff). While it is hunting:
   ```bash
   ros2 param set /mission_control angular_gain 12.0   # watch it overshoot / orbit
   ros2 param set /mission_control angular_gain 1.0    # watch it swing wide
   ros2 param set /mission_control linear_gain 4.0     # faster, sloppier
   ```
   The behaviour changes with no restart and no recompile. That is what
   **parameters** are for.

4. **Cancel it** (the other half of what makes an action an action). Start a big
   mission and abort it halfway:
   ```bash
   ros2 run turtle_capstone mission_client 20
   # ...let it catch a few, then press Ctrl-C
   ```
   The turtle stops where it is and the server reports how many it managed:
   `mission canceled after 4 catches`. Say: "you cannot cancel a service call.
   You can cancel an action. That is why navigation is an action."

5. **Inspect the internals** with the tools from
   [lesson 15](15-tools-and-debugging.md):
   ```bash
   ros2 action list
   ros2 action info /catch_mission -t
   ros2 topic echo /alive_turtles
   ros2 topic hz /turtle1/cmd_vel
   ```

---

## 5 — The glimpse: the same idea, on a walking robot

Close by showing that none of this was turtle-specific. The four-legged robot in
[Part 6](README.md#part-6--a-four-legged-robot) is driven by the **exact same
`/cmd_vel` Twist** the turtle used:

```bash
# Terminal 1 — robot model + gait controller + RViz (no simulator needed)
ros2 launch spider_bot walk.launch.py

# Terminal 2 — drive it with the same message type as the turtle
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"    # walk
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.6}}"   # turn
```

The turtle turned `/cmd_vel` into one wheel motion; the spider turns the *same
message* into twelve coordinated joint angles via inverse kinematics and a trot
gait ([lessons 20–21](20-leg-kinematics.md)). **The interface did not change —
only the maths in the middle.** That is the whole promise of ROS 2, and it is
the sentence to end the course on.

> Note: `walk.launch.py` needs only RViz, so it is the reliable one to demo live.
> The physics version, `gazebo.launch.py`, additionally needs classic Gazebo
> ([lesson 18](18-gazebo-simulation.md)).

---

## What you have now covered

| Concept | Where it shows up in the finale |
|---|---|
| Nodes | `mission_control` + `turtlesim` |
| Topics | `/turtle1/pose`, `/turtle1/cmd_vel`, `/alive_turtles` |
| Services | `/spawn`, `/kill` (called by `mission_control`) |
| Parameters + YAML | `grand_finale.yaml`, retuned live |
| Actions | `/catch_mission` — goal, feedback, result, cancel |
| Executors / callback groups | reentrant group + multi-threaded executor in the server |
| Control loops | the P-controller inside the mission |

That is every one of your teaching topics, running at once, in one window — and
a straight line from it to a real robot.

**Back to:** [the course index](README.md)
