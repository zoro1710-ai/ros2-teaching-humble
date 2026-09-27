# Class 01 — ROS 2 concepts with turtlesim

You won't write code today. You will try **nodes, topics, services,
parameters and actions** from the terminal. After each one, the
**Behind the scenes** box shows the few lines of Python that do the same job.

> **Secret:** every `ros2 topic pub` or `ros2 service call` quietly starts a
> tiny node of its own, runs those same lines, and then exits.

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

**Behind the scenes: a node is just this**
```python
import rclpy
from rclpy.node import Node

rclpy.init()                 # connect to ROS 2
node = Node('turtlesim')     # a node = an object with a name
rclpy.spin(node)             # stay alive and wait for work, forever
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

**Behind the scenes: publishing (what teleop and `topic pub` do)**
```python
pub = node.create_publisher(Twist, '/turtle1/cmd_vel', 10)  # "I will talk on this topic"
msg = Twist()                # an empty velocity message
msg.linear.x = 2.0           # fill it: forward speed
msg.angular.z = 1.8          # fill it: turning speed
pub.publish(msg)             # send it; whoever is listening gets it
```

**Behind the scenes: subscribing (what `topic echo` and turtlesim do)**
```python
def on_pose(msg):            # runs automatically every time a message arrives
    print(msg.x, msg.y)

node.create_subscription(Pose, '/turtle1/pose', on_pose, 10)  # "call on_pose for every message"
```
The publisher doesn't know who is listening, and the subscriber doesn't know
who is talking. They only share the topic name and the message type.

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

**Behind the scenes: the server (inside turtlesim)**
```python
def spawn(request, response):         # runs once per call
    # ...draw a new turtle at request.x, request.y...
    response.name = request.name      # fill in the answer
    return response                   # send it back to the caller

node.create_service(Spawn, '/spawn', spawn)   # "answer calls on /spawn"
```

**Behind the scenes: the client (what `service call` does)**
```python
client = node.create_client(Spawn, '/spawn')
request = Spawn.Request(x=2.0, y=2.0, name='bob')
future = client.call_async(request)   # ask...
# ...wait until future is done, then read future.result().name
```
Unlike a topic, exactly one server answers, and only when someone asks.

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

**Behind the scenes: parameters**
```python
node.declare_parameter('background_r', 69)            # "I have this setting, default 69"
red = node.get_parameter('background_r').value         # read the current value
```
`ros2 param set` changes the value from outside, and the node reads the new
one the next time it looks. That's why nothing changed until `/clear` redrew the screen.

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

**Behind the scenes: the action server (inside turtlesim)**
```python
def rotate(goal_handle):
    while not facing(goal_handle.request.theta):   # a long job, many steps
        if goal_handle.is_cancel_requested:        # someone pressed F
            goal_handle.canceled()
            return RotateAbsolute.Result()
        turn_a_little()
        feedback = RotateAbsolute.Feedback(remaining=how_far_left())
        goal_handle.publish_feedback(feedback)     # "still turning, this much left"
    goal_handle.succeed()                          # "done!"
    return RotateAbsolute.Result(delta=total_turned())

ActionServer(node, RotateAbsolute, '/turtle1/rotate_absolute', rotate)
```
An action = a goal (what to do) + feedback while it runs + a result at the end + cancel.

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

## Where the real code lives

The boxes above are trimmed down. The full, runnable versions are in
[`src/ros2_basics_py/ros2_basics_py/`](../../src/ros2_basics_py/ros2_basics_py/):

| Concept | File |
|---|---|
| Node | `minimal_node.py` |
| Topic | `talker.py`, `listener.py` |
| Service | `add_two_ints_server.py`, `add_two_ints_client.py` |
| Parameter | `parameter_demo.py` |
| Action | `count_until_server.py`, `count_until_client.py` |

(turtlesim itself is written in C++, but the idea is line-for-line the same.)

---

## If something breaks

| Problem | Fix |
|---|---|
| `ros2: command not found` | `source /opt/ros/humble/setup.bash` |
| Arrow keys do nothing | Click on the teleop terminal first |
| Background colour didn't change | Call `/clear` after `param set` |
| Command errors on `{ ... }` | Copy-paste it; spaces after `:` matter |
| Turtle hit the wall | That's fine; teleport it back to the centre |
