# The course

Twenty-three lessons, in order. Each one is short, ends with something you
run, and builds on the one before it. Everything is written for
**Ubuntu 22.04 + ROS 2 Humble Hawksbill**.

If you only have an hour, do lessons 00 → 04. That is enough to write a node
that talks to another node, which is most of day-to-day ROS 2.

Parts 1–5 are ROS 2 itself. Part 6 builds a four-legged robot with it.

## Part 1 — Get running

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 00 | [Install and set up](00-install-and-setup.md) | Install Humble, source it, avoid the three classic setup traps |
| 01 | [ROS 2 fundamentals](01-ros2-fundamentals.md) | Explain nodes, topics, services, actions, and what DDS is doing |
| 02 | [Workspaces and packages](02-workspaces-and-packages.md) | Create a workspace, build it with colcon, create your own package |

## Part 2 — The four ways nodes talk

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 03 | [Nodes](03-nodes.md) | Write a node, use timers and the logger properly |
| 04 | [Topics](04-topics.md) | Publish and subscribe, and debug a topic from the CLI |
| 05 | [Services](05-services.md) | Write a server and both styles of client without deadlocking |
| 06 | [Custom interfaces](06-custom-interfaces.md) | Define your own .msg, .srv and .action files |
| 09 | [Actions](09-actions.md) | Handle long-running goals with feedback and cancellation |

## Part 3 — Making it configurable

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 07 | [Parameters](07-parameters.md) | Declare, describe, validate and live-update parameters |
| 08 | [Launch files](08-launch-files.md) | Start a whole system with one command, with remapping and YAML |

## Part 4 — Getting it right

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 10 | [Quality of Service](10-qos.md) | Diagnose the "my topic is dead" bug and pick the right profile |
| 11 | [Executors and callback groups](11-executors-and-callback-groups.md) | Explain why your node froze, and fix it |
| 12 | [TF2](12-tf2.md) | Publish and look up coordinate frames |
| 13 | [Lifecycle nodes](13-lifecycle-nodes.md) | Write a node the system integrator can start and stop on demand |
| 14 | [Testing](14-testing.md) | Unit-test and integration-test ROS 2 code, in CI |
| 15 | [Tools and debugging](15-tools-and-debugging.md) | Use rqt, rosbag2, ros2 doctor and the CLI to find problems fast |

## Part 5 — Put it together

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 16 | [Capstone: catch them all](16-capstone-catch-them-all.md) | Build a complete multi-node application with a control loop |

## Part 6 — A four legged robot

Everything above is communication. This part is an actual robot: a spider bot
with four 3-DOF legs that walks where you tell it.

| # | Lesson | You will be able to |
|---|--------|---------------------|
| 17 | [URDF and robot description](17-urdf-and-robot-description.md) | Describe a 12-joint robot with xacro and see it in RViz |
| 18 | [Gazebo simulation](18-gazebo-simulation.md) | Put it in a world with gravity, contacts and friction |
| 19 | [ros2_control](19-ros2-control.md) | Command real or simulated actuators instead of faking joint states |
| 20 | [Leg inverse kinematics](20-leg-kinematics.md) | Turn a foot position into three joint angles, and test it properly |
| 21 | [Gait generation](21-gait-generation.md) | Coordinate four legs into a trot that walks, strafes and turns |
| 22 | [Navigation for legged robots](22-navigation-for-legged-robots.md) | Bridge Nav2's /cmd_vel to a gait, and know what is still missing |

Part 6 runs in RViz alone up to lesson 21 — Gazebo is only needed for lessons
18 and 19, and it is a large install.

## Reference

- [Cheat sheet](cheatsheet.md) — every CLI command used in the course, on one page
- [Troubleshooting](troubleshooting.md) — the errors you will actually hit, and their fixes
- [Glossary](glossary.md) — the vocabulary, defined once

## How to use this repo

Every lesson points at real, runnable code in `src/`. Read the lesson, run the
code, then break it on purpose — the "Common mistakes" section in each lesson
tells you what to break and what the failure looks like. That is the fastest
way to build the instinct for reading ROS 2 error messages.

Exercises live in [`exercises/`](../exercises/README.md), with full solutions.
