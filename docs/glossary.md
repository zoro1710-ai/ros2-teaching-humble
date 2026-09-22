# Glossary

The vocabulary, defined once, in plain words.

---

**action** — The communication pattern for long tasks: send a goal, receive
progress feedback, get a result, cancel if you change your mind. Built from
three services and two topics. [Lesson 09](09-actions.md).

**ament** — ROS 2's build system conventions. `ament_python` for pure Python
packages, `ament_cmake` for C++ and for packages that generate interfaces.

**callback** — A function ROS calls for you when something happens: a message
arrived, a timer expired, a service request came in. Your code runs almost
entirely inside callbacks.

**callback group** — Decides which callbacks may run at the same time.
`MutuallyExclusiveCallbackGroup` (the default) never overlaps;
`ReentrantCallbackGroup` may. [Lesson 11](11-executors-and-callback-groups.md).

**client** — The side that sends a request to a service, or a goal to an
action.

**colcon** — The build tool. `colcon build` compiles every package in
`src/` and installs it into `install/`.

**coxa / femur / tibia** — the three segments of a leg, borrowed from insect
anatomy. Coxa = the hip that swings the leg sideways, femur = upper segment,
tibia = lower segment that reaches the ground. [Lesson 20](20-leg-kinematics.md).

**DDS** — Data Distribution Service: the middleware underneath ROS 2 that
handles discovery and message transport. You rarely touch it directly; QoS is
where it surfaces.

**depth** — How many messages the queue holds. The `10` in
`create_publisher(String, 'chatter', 10)`.

**discovery** — How nodes find each other automatically over the network, with
no master process (unlike ROS 1). It takes a moment, which is why the first
few messages are often missed.

**duty factor** — the fraction of a gait cycle a foot spends on the ground.
0.5 = trot, 0.75 = crawl. [Lesson 21](21-gait-generation.md).

**executor** — The loop that waits for callbacks to become ready and runs
them. `rclpy.spin(node)` runs a single-threaded one.
[Lesson 11](11-executors-and-callback-groups.md).

**forward kinematics (FK)** — joint angles in, end-effector position out. The
easy direction. [Lesson 20](20-leg-kinematics.md).

**frame** — A named coordinate system, such as `base_link` or `laser`.
[Lesson 12](12-tf2.md).

**future** — A placeholder for a result that has not arrived yet. Returned by
`call_async()` and `send_goal_async()`. You attach a callback with
`add_done_callback()` rather than waiting on it.

**gait** — the schedule of which feet are on the ground when.
[Lesson 21](21-gait-generation.md).

**goal** — What you ask an action server to do.

**interface** — A message, service or action type definition (`.msg`, `.srv`,
`.action`). [Lesson 06](06-custom-interfaces.md).

**inverse kinematics (IK)** — end-effector position in, joint angles out. The
useful direction, and the harder one. [Lesson 20](20-leg-kinematics.md).

**launch file** — A Python, XML or YAML file describing a set of nodes to
start, with their parameters and remappings.
[Lesson 08](08-launch-files.md).

**lifecycle node** — A node with a managed state machine (unconfigured →
inactive → active) so something else decides when it starts working.
[Lesson 13](13-lifecycle-nodes.md).

**link / joint** — the two things a URDF is made of: a rigid body, and the
connection between two rigid bodies. [Lesson 17](17-urdf-and-robot-description.md).

**message** — One piece of typed data sent on a topic. Also the `.msg` file
defining its structure.

**namespace** — A prefix applied to a node's names, such as `/robot1`. Lets
you run the same node twice without collisions.

**node** — One program doing one job, that can talk to other nodes. The unit
of a ROS 2 system. [Lesson 03](03-nodes.md).

**parameter** — A named setting belonging to one node, set from outside the
code. [Lesson 07](07-parameters.md).

**publisher** — The object that sends messages on a topic.

**QoS (Quality of Service)** — The delivery contract for a topic: reliability,
durability, history, depth. Incompatible QoS means the two sides never
connect. [Lesson 10](10-qos.md).

**quaternion** — How ROS stores a rotation: four numbers `(x, y, z, w)`.
`(0, 0, 0, 1)` means no rotation. Avoids the singularities of Euler angles.

**rclpy** — The Python client library for ROS 2. (`rclcpp` is the C++ one.)

**remapping** — Rewiring a name at launch time without changing the code:
`--ros-args -r chatter:=/robot/chatter`.

**request / response** — The two halves of a service call, defined by the two
halves of a `.srv` file.

**ros2_control** — the framework between your code and the actuators. Provides
controllers (position, velocity, trajectory) and a hardware abstraction, so the
same code runs in simulation and on a real robot.
[Lesson 19](19-ros2-control.md).

**rosdep** — Installs the system dependencies your `package.xml` declares.

**rqt** — The suite of graphical debugging tools: `rqt_graph`, `rqt_console`,
`rqt_plot`, `rqt_reconfigure`. [Lesson 15](15-tools-and-debugging.md).

**RViz** — The 3D visualiser. Shows TF frames, sensor data, robot models, maps.

**service** — Request/response communication between two nodes. Use it for
quick questions, not for long jobs. [Lesson 05](05-services.md).

**sourcing** — Running `source setup.bash` so a terminal knows where ROS and
your packages are. Required in every new terminal.

**spin** — Handing control to the executor so callbacks can run.
`rclpy.spin(node)`.

**stance / swing** — the two halves of a leg's gait cycle: foot planted and
pushing (stance), foot lifted and returning (swing).
[Lesson 21](21-gait-generation.md).

**subscriber / subscription** — The object that receives messages from a topic
and calls your callback.

**TF2** — The library that tracks the relationships between coordinate frames
over time and composes them for you. [Lesson 12](12-tf2.md).

**topic** — A named, typed, many-to-many stream of messages. Fire and forget:
the publisher does not know who is listening.
[Lesson 04](04-topics.md).

**transform** — The translation + rotation from one frame to another.

**transient local** — The durability setting that makes a publisher deliver
its last message to subscribers that join later. Often called *latched*.

**trot** — a four-legged gait where diagonal pairs of legs move together. The
usual default. [Lesson 21](21-gait-generation.md).

**turtlesim** — The little 2D simulator used for teaching. `ros2 run turtlesim
turtlesim_node`.

**underlay / overlay** — The ROS installation you source first (`/opt/ros/humble`)
is the underlay; your workspace (`install/setup.bash`) is the overlay on top
of it. The overlay wins for packages that exist in both.

**URDF** — Unified Robot Description Format: the XML that describes a robot's
links and joints. Usually written as **xacro**, which adds properties, maths
and macros. [Lesson 17](17-urdf-and-robot-description.md).

**workspace** — A folder with a `src/` directory that colcon builds. Usually
`~/ros2_ws`. [Lesson 02](02-workspaces-and-packages.md).

---

Back to [the course index](README.md) ·
[cheat sheet](cheatsheet.md) · [troubleshooting](troubleshooting.md)
