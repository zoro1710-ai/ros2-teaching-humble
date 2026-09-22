# 16 — Capstone: catch them all

**Goal:** build a complete multi-node application that uses every concept in
the course — topics, services, custom interfaces, parameters, launch files and
a real control loop.

**Code:** [`turtle_spawner.py`](../src/turtle_capstone/turtle_capstone/turtle_spawner.py),
[`turtle_controller.py`](../src/turtle_capstone/turtle_capstone/turtle_controller.py),
[`catch_them_all.launch.py`](../src/turtle_capstone/launch/catch_them_all.launch.py),
[`catch_them_all.yaml`](../src/turtle_capstone/config/catch_them_all.yaml)

---

## The game

Turtles appear at random positions in the turtlesim window. `turtle1` has to
drive to each one and "catch" it, which makes it disappear. Repeat forever.

Run it first, then read how it works:

```bash
ros2 launch turtle_capstone catch_them_all.launch.py
```

---

## The architecture

```
        ┌──────────────────┐   /spawn (srv)   ┌──────────────┐
        │  turtle_spawner  │ ───────────────> │  turtlesim   │
        │                  │   /kill  (srv)   │              │
        └──────────────────┘ ───────────────> └──────────────┘
             │        ▲                            │      ▲
/alive_turtles│        │/catch_turtle               │      │
   (topic)    │        │  (srv)          /turtle1/pose    /turtle1/cmd_vel
              ▼        │                  (topic)          (topic)
        ┌─────────────────────┐                │      │
        │  turtle_controller  │ <──────────────┘      │
        │                     │ ──────────────────────┘
        └─────────────────────┘
```

Two nodes you write, one you get for free:

| Node | Job |
|---|---|
| `turtlesim_node` | the simulator (provided by ROS) |
| `turtle_spawner` | creates turtles, removes caught ones, publishes the list |
| `turtle_controller` | reads the list and its own pose, drives towards a target |

Notice the division of labour. The spawner owns the *world state*. The
controller owns the *motion*. Neither reaches into the other — they talk over
a topic and a service. That separation is the design lesson of the capstone.

---

## The interfaces

Two custom messages and one custom service
([lesson 06](06-custom-interfaces.md)):

```
# msg/Turtle.msg
string name
float64 x
float64 y
float64 theta
```

```
# msg/TurtleArray.msg
Turtle[] turtles
```

```
# srv/CatchTurtle.srv
string name
---
bool success
```

Why a topic for the list and a service for the catch? The list is *state* that
changes continuously and many nodes might want — that is a topic. Catching is
a *request* with an answer ("did that work?") — that is a service. Getting
this choice right is most of ROS 2 design.

---

## The spawner

[`turtle_spawner.py`](../src/turtle_capstone/turtle_capstone/turtle_spawner.py)
is a pure orchestration node: it owns no hardware and does almost no maths. It
calls other nodes' services and keeps a list.

```python
    def __init__(self):
        super().__init__('turtle_spawner')

        self.declare_parameter('spawn_frequency', 0.5)
        self.declare_parameter('turtle_name_prefix', 'turtle')

        self._spawn_frequency = self.get_parameter('spawn_frequency').value
        self._prefix = self.get_parameter('turtle_name_prefix').value

        # turtlesim always starts with turtle1, so our first one is turtle2.
        self._counter = 1
        self._alive_turtles = []

        self._publisher = self.create_publisher(TurtleArray, 'alive_turtles', 10)
        self._spawn_client = self.create_client(Spawn, 'spawn')
        self._kill_client = self.create_client(Kill, 'kill')
        self._catch_service = self.create_service(
            CatchTurtle, 'catch_turtle', self.on_catch_request)

        self._timer = self.create_timer(1.0 / self._spawn_frequency, self.spawn_turtle)
```

One node with a publisher, two clients, a service server and a timer — which
is exactly what a real ROS 2 node looks like.

### Spawning

```python
    def spawn_turtle(self):
        if not self._spawn_client.service_is_ready():
            self.get_logger().info('waiting for the /spawn service ...')
            return

        self._counter += 1
        name = '%s%d' % (self._prefix, self._counter)

        request = Spawn.Request()
        request.x = random.uniform(1.0, 10.0)
        request.y = random.uniform(1.0, 10.0)
        request.theta = random.uniform(0.0, 2.0 * math.pi)
        request.name = name

        future = self._spawn_client.call_async(request)
        # partial() binds the turtle we asked for to the callback, because the
        # callback signature only gives us the future.
        future.add_done_callback(
            partial(self.on_spawn_response, name=name, x=request.x, y=request.y,
                    theta=request.theta))
```

- `service_is_ready()` is the **non-blocking** check. Calling
  `wait_for_service()` here would freeze the node
  ([lesson 11](11-executors-and-callback-groups.md)).
- `call_async` + `add_done_callback` — the timer returns immediately and the
  answer is handled later.
- **`functools.partial`** is the piece worth stealing. A done-callback receives
  only the future, so it has no idea *which* request it belongs to. `partial`
  binds the extra context at the moment you send the request:

```python
def on_spawn_response(self, future, name, x, y, theta):
    ...
```

Without it you would need a dictionary of pending requests, which is what
`partial` saves you from.

### Catching

```python
    def on_catch_request(self, request, response):
        if not any(turtle.name == request.name for turtle in self._alive_turtles):
            self.get_logger().warn('%s is not alive' % request.name)
            response.success = False
            return response

        self.call_kill(request.name)
        response.success = True
        return response
```

The service callback validates, kicks off the `/kill` call **without waiting
for it**, and answers straight away. The list is only updated once `/kill`
actually succeeds, in `on_kill_response`. That is the right order: do not
claim something happened before it did.

---

## The controller

[`turtle_controller.py`](../src/turtle_capstone/turtle_capstone/turtle_controller.py)
is where the robotics lives.

### Inputs

```python
    def on_pose(self, msg):
        self._pose = msg

    def on_alive_turtles(self, msg):
        if not msg.turtles:
            self._target = None
            return

        if self._catch_closest_first and self._pose is not None:
            self._target = min(msg.turtles, key=self.distance_to)
        else:
            # Oldest first: the spawner appends, so index 0 is the oldest.
            self._target = msg.turtles[0]
```

Both callbacks are tiny: they store data and return. **No control logic in a
subscription callback.** The thinking happens on a timer, at a fixed rate,
which is what makes the behaviour predictable.

### The control loop

```python
    def control_loop(self):
        if self._pose is None or self._target is None:
            # Nothing to chase: publish a zero command so the turtle coasts
            # to a stop instead of keeping its last velocity.
            self._cmd_publisher.publish(Twist())
            return

        distance = self.distance_to(self._target)
        cmd = Twist()

        if distance > self._catch_distance:
            # Proportional control on distance and on heading error.
            target_heading = math.atan2(
                self._target.y - self._pose.y, self._target.x - self._pose.x)
            heading_error = normalize_angle(target_heading - self._pose.theta)

            cmd.linear.x = self._linear_gain * distance
            cmd.angular.z = self._angular_gain * heading_error
        else:
            caught = self._target
            self._target = None
            self.call_catch_turtle(caught.name)

        self._cmd_publisher.publish(cmd)
```

This is a **proportional (P) controller**, the simplest useful feedback
controller there is:

```
error   = where I want to be  −  where I am
command = gain × error
```

Two errors drive two commands:

| Error | Command | Code |
|---|---|---|
| distance to the target | forward speed | `cmd.linear.x = linear_gain * distance` |
| angle between my heading and the target | turn rate | `cmd.angular.z = angular_gain * heading_error` |

`math.atan2(dy, dx)` gives the direction to the target in world coordinates.
Subtracting the turtle's own heading gives how far it must turn.

And then the detail that makes it work:

```python
def normalize_angle(angle):
    """Wrap an angle in radians into the range [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle
```

Without this, an error of `+350°` stays `+350°` and the turtle spins almost
all the way around instead of turning `-10°`. Normalising means it always
takes the short way.

The `if self._pose is None` guard matters too: for the first few milliseconds
no pose has arrived, and `control_loop` runs at 100 Hz from the start.

---

## Tying it together

[`catch_them_all.yaml`](../src/turtle_capstone/config/catch_them_all.yaml)
holds every tunable number, so behaviour changes need no code changes:

```yaml
turtle_spawner:
  ros__parameters:
    spawn_frequency: 0.5       # new turtles per second
    turtle_name_prefix: "turtle"

turtle_controller:
  ros__parameters:
    catch_closest_first: true
    linear_gain: 2.0
    angular_gain: 6.0
    catch_distance: 0.5        # metres, in turtlesim units
    control_period: 0.01       # 100 Hz control loop
```

And [`catch_them_all.launch.py`](../src/turtle_capstone/launch/catch_them_all.launch.py)
starts all three nodes:

```python
    controller = Node(
        package='turtle_capstone',
        executable='turtle_controller',
        name='turtle_controller',
        output='screen',
        parameters=[
            config,
            # Later entries win, so this CLI argument overrides the YAML value.
            {'catch_closest_first': ParameterValue(
                LaunchConfiguration('catch_closest_first'), value_type=bool)},
        ],
    )
```

The `parameters=[config, {override}]` idiom — file first, command-line
override second — is worth remembering. It is how you keep a sensible default
configuration and still experiment from the terminal.

---

## Try it

```bash
ros2 launch turtle_capstone catch_them_all.launch.py
```

Chase the oldest turtle instead of the nearest one, and watch the path change:

```bash
ros2 launch turtle_capstone catch_them_all.launch.py catch_closest_first:=false
```

Tune it live, while it runs ([lesson 07](07-parameters.md)):

```bash
ros2 param set /turtle_controller linear_gain 4.0     # faster, less accurate
ros2 param set /turtle_controller angular_gain 12.0   # watch it overshoot
ros2 param set /turtle_controller angular_gain 1.0    # watch it swing wide
```

Raising the gains too far makes the controller overshoot and orbit its target
forever — a visible, hands-on demonstration of what a P controller cannot do.

Inspect it with everything from [lesson 15](15-tools-and-debugging.md):

```bash
ros2 node list
ros2 topic echo /alive_turtles
ros2 topic hz /turtle1/cmd_vel
rqt_graph
ros2 run rqt_plot rqt_plot /turtle1/pose/x /turtle1/pose/y
```

---

## Make it yours

In rough order of difficulty:

1. **Log the score.** Count catches and print a running total with the elapsed
   time.
2. **Stop cleanly.** Add a `/pause` service (`std_srvs/srv/SetBool`) that makes
   the controller publish zero velocity until resumed.
3. **Cap the population.** Add a `max_turtles` parameter; stop spawning above
   it and resume when the count drops.
4. **Slow down at the end.** Clamp `cmd.linear.x` to a `max_speed` parameter so
   the turtle stops overshooting small distances.
5. **Turn it into an action.** Replace `/catch_turtle` with a `CatchTurtle`
   *action* that reports the remaining distance as feedback and can be
   cancelled ([lesson 09](09-actions.md)).
6. **Test the maths.** `normalize_angle` and `distance_to` are pure functions.
   Write unit tests for them ([lesson 14](14-testing.md)) — including the
   `+350°` case.
7. **Add a PD term.** Keep the previous heading error, and subtract
   `kd * (error - previous_error) / dt`. It damps the overshoot you saw when
   you raised the gains.

---

## Common mistakes

**The turtle spins in circles and never arrives.**
`normalize_angle` is missing or wrong, or `angular_gain` is far too high.

**The turtle drifts off after catching the last one.**
The zero-`Twist` publish in the "nothing to chase" branch is missing.
`cmd_vel` is a *latched intent*: turtlesim keeps the last command.

**`AttributeError: 'NoneType' object has no attribute 'x'`**
The control loop ran before the first pose arrived. Keep the `None` guard.

**Nothing spawns.**
turtlesim is not running, or the spawner is waiting on `/spawn`. Check
`ros2 service list`.

**The controller chases a turtle that is already dead.**
The `alive_turtles` list updates on `/kill` success, so there is a brief
window. Clearing `self._target` at the moment of catching (as the code does)
is what prevents it.

**The node freezes when catching.**
You used `wait_for_service()` or a blocking `call()` inside a callback. Use
`service_is_ready()` + `call_async` ([lesson 11](11-executors-and-callback-groups.md)).

---

## What you have now covered

| Concept | Where it shows up in the capstone |
|---|---|
| Nodes, timers, logging | both nodes |
| Topics | `/alive_turtles`, `/turtle1/pose`, `/turtle1/cmd_vel` |
| Services (server and client) | `/catch_turtle`, `/spawn`, `/kill` |
| Custom interfaces | `Turtle`, `TurtleArray`, `CatchTurtle` |
| Parameters + YAML | `catch_them_all.yaml` |
| Launch files | `catch_them_all.launch.py` |
| Non-blocking design | `call_async` + `partial` everywhere |
| Control loops | the P controller |

That is a complete ROS 2 application. Everything you build from here — a real
robot base, a navigation stack, a manipulator — is this same set of pieces,
with better maths in the middle.

---

**Where to go next:** [Nav2](https://navigation.ros.org/) for autonomous
navigation, [MoveIt 2](https://moveit.ros.org/) for manipulation,
[ros2_control](https://control.ros.org/) for real hardware, and URDF + Gazebo
to simulate a robot of your own.

**Back to:** [the course index](README.md)
