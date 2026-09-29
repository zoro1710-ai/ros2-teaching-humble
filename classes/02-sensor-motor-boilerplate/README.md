# Class 02: any sensor into ROS, and motors on the keyboard

One boilerplate for every microcontroller project in this course:

```
 ┌──────────── ESP32 / Arduino ───────────┐   USB    ┌──────────── PC (ROS 2) ─────────────┐
 │ Sensor objects ── "S range sonar 0.42" ─┼────────►┼─ mcu_bridge ──► /sensors/sonar      │
 │                                         │         │                                    │
 │ Motors  ◄──────── "M 0.500 0.500" ──────┼◄────────┼─ mcu_bridge ◄── /cmd_vel ◄── keyboard_teleop
 └─────────────────────────────────────────┘         └────────────────────────────────────┘
```

- **Adding a sensor** means one small class on the board. The PC creates `/sensors/<name>` by itself.
- **Driving** means any node that publishes `/cmd_vel`. Today that's the keyboard. Later it's your own code, then Nav2.

| Where | What |
|---|---|
| [`firmware/mcu_bridge/`](../../firmware/mcu_bridge) | Arduino sketch: sensors + motors + watchdog |
| [`src/mcu_bridge/`](../../src/mcu_bridge) | ROS 2 package: `mcu_bridge` node, `keyboard_teleop` node |

Why not micro-ROS? It's a good tool, but its setup eats a whole class. This protocol is
plain text: you can **read it and type it** in the Serial Monitor, and it runs on a $3 Uno.
Once you understand this, micro-ROS is the same idea with more machinery.

---

## 1. No hardware yet? Start with the pretend board

```bash
colcon build --packages-select mcu_bridge && source install/setup.bash
```

**Terminal 1**
```bash
ros2 launch mcu_bridge bridge.launch.py          # port defaults to 'sim'
```

**Terminal 2**
```bash
ros2 run mcu_bridge keyboard_teleop               # press w, then s to stop
```

**Terminal 3**
```bash
ros2 topic list                                   # /sensors/front_sonar, /sensors/ldr
ros2 topic echo /sensors/front_sonar --field range
```

Hold `w` and watch the range shrink: the pretend robot is driving at a wall.
Close Terminal 2 and the log says the motors went to 0 about half a second later.

**Test the keys on turtlesim first.** It's the same `/cmd_vel` idea, just a different topic name:
```bash
ros2 run turtlesim turtlesim_node
ros2 run mcu_bridge keyboard_teleop --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

---

## 2. The real board

### Shopping list (about $10)
| Part | Notes |
|---|---|
| ESP32 DevKit **or** Arduino Uno | ESP32 recommended |
| L298N or TB6612FNG motor driver | TB6612 wastes less battery |
| 2 × TT gear motors + wheels + caster | the yellow ones |
| Battery pack 6–7.4 V | **never** power motors from USB |
| HC-SR04 ultrasonic, LDR + 10 kΩ | the two example sensors |

### Wiring
All pins live in [`config.h`](../../firmware/mcu_bridge/config.h). It picks ESP32 or Uno pins automatically.

| Driver pin | ESP32 | Uno |
|---|---|---|
| ENA (left PWM) | 25 | 5 |
| IN1 / IN2 | 26 / 27 | 7 / 8 |
| ENB (right PWM) | 32 | 6 |
| IN3 / IN4 | 33 / 13 | 11 / 12 |
| GND | GND | GND |

> ⚠️ **Connect the battery GND to the board GND.** Without that common ground the motors twitch at random.
> ⚠️ **L298N: pull off the ENA/ENB jumpers**, otherwise speed control does nothing.
> ⚠️ **ESP32 + HC-SR04:** ECHO is 5 V. Use a 1 kΩ / 2 kΩ divider.

### Flash it
1. Open `firmware/mcu_bridge/mcu_bridge.ino` in the Arduino IDE.
2. Select the board and port, then upload.
3. **Test without ROS:** Serial Monitor at 115200 with the line ending set to *Newline*. You should see:
   ```
   I ready with 2 sensors
   S light ldr 1843.0000
   S range front_sonar 0.3120
   ```
   Type `M 0.5 0.5`. Both wheels should spin forward for half a second, then the watchdog stops them.
   **If a wheel spins backwards, set `LEFT_INVERTED` or `RIGHT_INVERTED` to true.**
   Swapping wires also works, but the flag is quicker.

### Run it with ROS
Close the Serial Monitor first, because only one program can own the port.

```bash
ls /dev/ttyUSB* /dev/ttyACM*                      # find the port
sudo usermod -aG dialout $USER                    # once, then log out and back in
ros2 launch mcu_bridge bridge.launch.py port:=/dev/ttyUSB0
ros2 run mcu_bridge keyboard_teleop               # second terminal
```

> **WSL users:** Windows owns USB. In an *admin* PowerShell:
> `usbipd list` → `usbipd bind --busid <id>` → `usbipd attach --wsl --busid <id>`.

---

## 3. Add your own sensor (the whole point)

Example: a potentiometer on pin 35 (use A1 on an Uno).

**Board**: copy [`SensorTemplate.h`](../../firmware/mcu_bridge/SensorTemplate.h). For simple analog parts you can even reuse `SensorAnalog`. Then in `mcu_bridge.ino`:

```cpp
// (2) create it: type, name, every 50 ms, pin
SensorAnalog knob("knob", "pot", 50, 35);

// (3) list it
Sensor* SENSORS[] = {&light, &sonar, &knob};
```

Upload. Restart the bridge. Done:

```bash
ros2 topic echo /sensors/pot          # std_msgs/Float32MultiArray
ros2 run rqt_plot rqt_plot /sensors/pot/data[0]
```

**Want a proper ROS message type?** The `type` word decides it:

| `type` on the board | You get on the PC | Values the board must send |
|---|---|---|
| `range` | `sensor_msgs/Range` | distance in m (`inf` = nothing) |
| `imu` | `sensor_msgs/Imu` | ax ay az (m/s²) gx gy gz (rad/s) |
| `temperature` | `sensor_msgs/Temperature` | °C |
| anything else | `std_msgs/Float32MultiArray` | whatever you like |

To add a new type, write one small function in
[`converters.py`](../../src/mcu_bridge/mcu_bridge/converters.py) and add it to `CONVERTERS`.

> **Rule of thumb:** send **SI units** from the board (metres, m/s², rad/s, °C).
> Every ROS tool expects them, and conversion bugs are easier to fix in C++ on the board than to hunt for later.

---

## 4. Exercises

1. **Sonar brake.** Write a node that subscribes to `/sensors/front_sonar` and `/cmd_vel_key`,
   and republishes to `/cmd_vel` but with forward speed set to 0 when range < 0.2 m.
   Run teleop with `-r cmd_vel:=/cmd_vel_key`. *(Topics, remapping, your first safety layer.)*
2. **See the sonar in RViz.** Run `rviz2`, add a *Range* display on `/sensors/front_sonar`,
   and type `front_sonar_link` as the Fixed Frame. Move your hand and watch the cone.
   Then set the Fixed Frame to `base_link`. Why does it break, and why does this fix it?
   `ros2 run tf2_ros static_transform_publisher --x 0.1 --frame-id base_link --child-frame-id front_sonar_link`
3. **Enable the MPU6050.** Uncomment its two lines in the sketch and add `&imu` to `SENSORS`. Tilt the board while
   `rqt_plot` shows `/sensors/imu/linear_acceleration/x` and `/z`. Where did gravity go?
4. **Light follower.** Add a second LDR (`ldr_right`) and write a node that steers towards the brighter side.
5. **Touch D-pad** (ESP32 only). Make a `SensorTouch` from the template using `touchRead(pin)`,
   and drive the turtle with foil pads.
6. **Break it on purpose.** Unplug the USB while driving. What does the bridge log say,
   what do the wheels do, and which of the two watchdogs stopped them?

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cannot open /dev/ttyUSB0 ... Permission denied` | `dialout` group (see above), then log out and back in |
| `cannot open ... Device or resource busy` | Close the Arduino Serial Monitor |
| `no newline in 1 KB of data` | Baud mismatch between `config.h` and `bridge.yaml` |
| Topic appears but never updates | Sensor `read()` returns 0; check wiring |
| Wheels hum but don't turn | Raise `MIN_PWM` in `config.h`; check battery |
| Robot drives backwards on `w` | Set both `*_INVERTED` flags |
| Turns the wrong way on `a` | Left and right motors are swapped: swap them in `config.h` |
| ESP32 resets when the motors start | Battery too weak / shared supply; motors must not run off USB |
