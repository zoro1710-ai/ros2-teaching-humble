# Class 01 — ROS 2 concepts with turtlesim

No code today. You will try **nodes, topics, services, parameters and
actions** from the terminal alone.

> Copy and paste the commands instead of typing them. One typo in `{ ... }` breaks them.

**Before every new terminal:**

```bash
source /opt/ros/humble/setup.bash   # loads ROS 2 into this terminal
```

---

## The 5 words

| Word | Think of it as | Example |
|---|---|---|
| **Node** | One small program with one job | The turtle simulator |
| **Topic** | Radio station: broadcast, anyone listens, no reply | Turtle's position, sent non-stop |
| **Service** | Phone call: ask once, wait, get an answer | "Spawn a new turtle" |
| **Parameter** | A setting you can change while it runs | Background colour |
| **Action** | Pizza order: a long task with progress updates, can cancel | "Rotate to face left" |

---

## 1. Nodes: start the programs

**Terminal 1**
```bash
ros2 run turtlesim turtlesim_node      # start the turtle window (node 1)
```

**Terminal 2**
```bash
ros2 run turtlesim turtle_teleop_key   # arrow keys drive the turtle (node 2)
```
Click on this terminal before pressing keys.

**Terminal 3**
```bash
ros2 node list                         # show every running node
ros2 node info /turtlesim              # what this node sends, receives and offers
rqt_graph                              # draw a picture: nodes = circles, topics = arrows
```

---

## 2. Topics: data that flows non-stop

```bash
ros2 topic list                        # every topic that exists right now
ros2 topic info /turtle1/cmd_vel       # who publishes and who subscribes to it
ros2 topic echo /turtle1/pose          # print the turtle's position live (Ctrl+C to stop)
ros2 topic hz /turtle1/pose            # how many messages per second
ros2 interface show geometry_msgs/msg/Twist   # what a velocity message looks like
```

Now **you** act as the teleop node:

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0}}"
```
Sends one message: move forward at 2.0.

```bash
ros2 topic pub -r 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0}, angular: {z: 1.8}}"
```
Sends it once every second (`-r 1`): forward plus turning, so it draws a circle. Ctrl+C stops it.

**Try:** change `x` and `z` to make a bigger circle, then a smaller one.

---

## 3. Services: ask once, get an answer

```bash
ros2 service list                                  # every service you can call
ros2 interface show turtlesim/srv/Spawn            # what you send / what comes back
```

```bash
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 2.0, theta: 0.0, name: 'bob'}"
```
Asks the simulator to create a turtle named `bob` at (2, 2). The reply is its name.

```bash
ros2 service call /turtle1/set_pen turtlesim/srv/SetPen "{r: 255, g: 0, b: 0, width: 5, 'off': 0}"
```
Changes turtle1's pen to red, 5 pixels wide. `'off': 1` lifts the pen.

```bash
ros2 service call /turtle1/teleport_absolute turtlesim/srv/TeleportAbsolute "{x: 5.5, y: 5.5, theta: 0.0}"
```
Jumps the turtle to the centre instantly.

```bash
ros2 service call /clear std_srvs/srv/Empty       # wipe the drawings
ros2 service call /kill turtlesim/srv/Kill "{name: 'bob'}"   # remove bob
```

**Try:** spawn 3 turtles and give each one a different pen colour.

---

## 4. Parameters: settings you change live

```bash
ros2 param list /turtlesim                         # all settings of this node
ros2 param get /turtlesim background_r             # read one setting
ros2 param set /turtlesim background_r 255         # change it while the node runs
ros2 service call /clear std_srvs/srv/Empty       # redraw so the new colour shows
```
Colours use `background_r`, `background_g` and `background_b`, each from 0 to 255.

**Try:** change the background to your team's colour.

---

## 5. Actions: long tasks with progress

```bash
ros2 action list                                   # every action available
ros2 action info /turtle1/rotate_absolute          # who serves it
ros2 interface show turtlesim/action/RotateAbsolute   # goal / result / feedback
```

```bash
ros2 action send_goal --feedback /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 3.14}"
```
Goal: face left (3.14 radians = 180°). `--feedback` prints how far it has left to turn,
and the result arrives at the end.

**Cancel it:** in the teleop terminal, `G B V C D E R T` also send rotate goals, and
**`F` cancels** one halfway.

**Think:** why is "rotate" an action and not a service?

---

## Which one would you use?

| Situation | Answer |
|---|---|
| Camera sending images | Topic |
| "Is the gripper closed?" | Service |
| "Drive to the kitchen, tell me progress" | Action |
| Robot's maximum speed | Parameter |
| Battery level every second | Topic |
| "Take one photo now" | Service |

---

## If something breaks

| Problem | Fix |
|---|---|
| `ros2: command not found` | `source /opt/ros/humble/setup.bash` |
| Arrow keys do nothing | Click on the teleop terminal first |
| Background colour didn't change | Call `/clear` after `param set` |
| Command errors on `{ ... }` | Copy-paste it; spaces after `:` matter |
| Turtle hit the wall | That's fine; teleport it back to the centre |
