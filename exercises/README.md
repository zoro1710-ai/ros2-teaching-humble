# Exercises

Eight practice problems, one per major concept, each with a **complete
solution** at the bottom of the page.

Do them in order. Each one assumes you finished the matching lesson.

| # | Exercise | After lesson | You will write |
|---|---|---|---|
| 01 | [Your first node](01-first-node.md) | [03 — Nodes](../docs/03-nodes.md) | a node with a timer |
| 02 | [Publisher and subscriber](02-publisher-subscriber.md) | [04 — Topics](../docs/04-topics.md) | two nodes talking over a topic |
| 03 | [A service](03-service.md) | [05 — Services](../docs/05-services.md) | a server and a non-blocking client |
| 04 | [A custom interface](04-custom-interface.md) | [06 — Custom interfaces](../docs/06-custom-interfaces.md) | your own .msg and .srv |
| 05 | [Parameters](05-parameters.md) | [07 — Parameters](../docs/07-parameters.md) | a node you can retune live |
| 06 | [A launch file](06-launch-file.md) | [08 — Launch files](../docs/08-launch-files.md) | one command to start it all |
| 07 | [An action](07-action.md) | [09 — Actions](../docs/09-actions.md) | goal, feedback, cancel |
| 08 | [Find the QoS bug](08-qos.md) | [10 — QoS](../docs/10-qos.md) | nothing — you debug |

---

## How to work on these

Create a scratch package once and put every exercise in it:

```bash
cd ~/ros2_ws/src
ros2 pkg create my_exercises --build-type ament_python \
    --dependencies rclpy std_msgs example_interfaces
```

Then for each exercise:

1. Write the node(s) in `my_exercises/my_exercises/`.
2. Add an entry to `console_scripts` in `setup.py`.
3. `cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash`
4. Run it and check it with the CLI tools.

With `--symlink-install` you only need to rebuild when you add a new entry
point, not on every code change.

---

## Rules that will save you time

- **Read the error message.** ROS 2 errors are long but the first line is
  usually the whole story.
- **Check with the CLI before you debug the code.** `ros2 node list`,
  `ros2 topic info /x --verbose`, `ros2 service list`.
- **Build, then source, in every terminal.**
- Stuck for more than ten minutes? Look at the solution, understand it, close
  it, and type it out yourself. That is not cheating; retyping is how it
  sticks.

[Troubleshooting](../docs/troubleshooting.md) has the common errors.
