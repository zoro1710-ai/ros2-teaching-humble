# Class 04: spin an N20 motor with the STM32 Black Pill

Before ROS can drive anything, the board has to drive a motor. Today: one N20 gear motor,
forward and backward, then speed, then the keyboard, then two of them like the Defender's shooter,
and finally ROS driving them.

```
 ┌─── Black Pill ───┐  3 wires   ┌── TB6612FNG ──┐  2 wires  ┌─ N20 ─┐
 │ PA8  (speed)     ├───────────►┤ PWMA      AO1 ├──────────►┤   M   │
 │ PB12 (direction) ├───────────►┤ AIN1      AO2 ├──────────►┤       │
 │ PB13 (direction) ├───────────►┤ AIN2          │           └───────┘
 └──────────────────┘            │ VM ◄── motor battery
                                 └───────────────┘
```

**Why a driver?** A Black Pill pin gives about 20 mA at 3.3 V. An N20 wants 100–500 mA, and more when it stalls.
The pin only *tells* the driver what to do; the driver takes the power from the battery.

| Sketch | What it teaches |
|---|---|
| [`01_blink`](01_blink/01_blink.ino) | Upload works, board is alive (no motor) |
| [`02_forward_backward`](02_forward_backward/02_forward_backward.ino) | Two direction pins + one speed pin |
| [`03_speed_ramp`](03_speed_ramp/03_speed_ramp.ino) | PWM = speed; one signed number for speed + direction |
| [`04_serial_control`](04_serial_control/04_serial_control.ino) | Type `f` `b` `s` `0`–`9` to drive it |
| [`05_two_motors`](05_two_motors/05_two_motors.ino) | Two N20s spinning opposite: the shooter flywheels |
| [`mcu_bridge`](../../firmware/mcu_bridge/mcu_bridge.ino) (from class 02) | The same motors, driven by ROS `/cmd_vel` instead of the Serial Monitor |

Each sketch is in its own folder because the Arduino IDE needs the folder name to match the `.ino` name.

---

## 1. Shopping list

| Part | Notes |
|---|---|
| STM32F411 (or F401) **Black Pill** | the blue WeAct board with USB-C |
| **TB6612FNG** motor driver | works fine with 3.3 V logic, 2 motors, 1.2 A each |
| N20 gear motor (×2 for sketch 05) | check its voltage: **3 V, 6 V or 12 V** is printed on the label/listing |
| Motor battery | matches the motor: 2×AA (3 V), 4×AA or 2S Li-ion (6–7.4 V) for 6 V N20s |
| Breadboard + jumpers, USB-C **data** cable | many cheap USB-C cables are charge-only |

> A DRV8833 board also works and uses the same idea (but only 2 input pins per motor, no PWM pin).
> An L298N also works but wastes about 2 V as heat, which is a lot for a 6 V N20.

---

## 2. Wiring

| TB6612FNG | Black Pill | Why |
|---|---|---|
| PWMA | **PA8** | speed (a PWM pin) |
| AIN1 | **PB12** | direction |
| AIN2 | **PB13** | direction |
| STBY | **PB14** | HIGH = driver on (or tie it straight to 3V3) |
| VCC | **3V3** | driver logic |
| GND | **G** | **common ground** |
| VM | battery **+** | motor power |
| GND (next to VM) | battery **−** | |
| AO1 / AO2 | the two N20 wires | |

For the second motor (sketch 05): **PWMB → PB6, BIN1 → PB15, BIN2 → PA10**, motor on BO1 / BO2.

> ⚠️ **Battery GND must connect to Black Pill GND.** Without it the motor twitches or does nothing.
> ⚠️ **Never power the motor from the Black Pill's 3V3 or 5V pin.** The spike when it starts will reset the board.
> ⚠️ **Don't use PA11 / PA12** (that's the USB) or **PA13 / PA14** (that's the programmer). PC13 is the LED.

How the two direction pins work:

| AIN1 | AIN2 | Motor |
|---|---|---|
| HIGH | LOW | forward |
| LOW | HIGH | backward |
| LOW | LOW | coast (stops by itself) |
| HIGH | HIGH | brake (stops hard) |

---

## 3. Set up the Arduino IDE for the Black Pill (once per laptop)

1. **File → Preferences → Additional boards manager URLs**, add:
   `https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json`
2. **Tools → Board → Boards Manager**, search **STM32 MCU based boards** (by STMicroelectronics), install.
3. Install **[STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html)**. The IDE uses it to upload.
4. In the **Tools** menu choose:

| Setting | Value |
|---|---|
| Board | Generic STM32F4 series |
| Board part number | **BlackPill F411CE** (or BlackPill F401CC for the F401 board) |
| USB support | **CDC (generic 'Serial' supersede U(S)ART)** |
| Upload method | **STM32CubeProgrammer (DFU)** |

### Uploading (the button dance)
The Black Pill has no auto-upload over USB. Put it in **DFU mode** every time:

1. **Hold BOOT0**
2. **Press and release NRST**
3. **Release BOOT0**
4. Click **Upload**. When it finishes, press **NRST** once so your sketch starts.

After the upload a new COM port appears. Pick it in **Tools → Port**, then open the Serial Monitor at 115200.

---

## 4. The class, step by step

### Step 1: `01_blink`
Upload it. The blue LED blinks and the Serial Monitor prints `tick`. If this doesn't work, **nothing else will**:
fix it before plugging in any motor (see Troubleshooting).

### Step 2: `02_forward_backward`
Wire the driver and motor. Upload. The motor runs 2 s forward, stops, 2 s backward, stops, forever.

*Ask the class:* what happens if you swap the two motor wires? What if you swap AIN1 and AIN2 in the code?
(Same thing. That's why "forward" is only a name until the robot is built.)

### Step 3: `03_speed_ramp`
Open **Tools → Serial Plotter**. You get a triangle wave, and the motor follows it.
Write down the number where the motor **starts** turning. Below it the N20 just hums, because the
gearbox friction is bigger than the push. That number goes into `MIN_PWM` in the next sketches.

`analogWriteFrequency(20000)` moves the PWM above human hearing. Comment it out and listen to the whine.

### Step 4: `04_serial_control`
Serial Monitor, then type:

```
5   f      half speed forward
9          full speed
b          backward (it stops for 0.2 s first, to save the gears)
s          stop
```

This is exactly the job the `mcu_bridge` firmware from class 02 does, just with letters instead of `M 0.5 0.5`.
Next step is replacing the human typing with a ROS node.

### Step 5: `05_two_motors`
Two N20s = the Defender's two flywheels. They must spin **opposite** ways so they pinch the dart
(the URDF says the same thing with `<mimic multiplier="-1">`). The code does it with `RIGHT_INVERTED = true`,
not by rewiring. It also **ramps** the speed, because two motors starting at once can pull the battery voltage
down enough to reset the board.

### Step 6: drive it from ROS (no Serial Monitor)
Same wiring as sketch 05 (motor A = left, motor B = right; one motor on A is fine too).
Now the Black Pill runs the class 02 bridge firmware, and **ROS sends the commands instead of you**.

```
 keyboard_teleop ──► /cmd_vel ──► mcu_bridge node ──"M 0.40 0.40"──USB──► Black Pill ──► TB6612 ──► N20s
     (PC)                            (PC)
```

**1. Flash the bridge firmware.** Open [`firmware/mcu_bridge/mcu_bridge.ino`](../../firmware/mcu_bridge/mcu_bridge.ino)
(not a class 04 sketch). The Black Pill pins are already in [`config.h`](../../firmware/mcu_bridge/config.h),
picked automatically for STM32 boards. Set `MIN_PWM` in `config.h` to the number you found in step 3.
Same Tools settings and BOOT0 / NRST dance as before, then press **NRST**.

**2. Close the Arduino Serial Monitor.** Only one program can own the port, and now that's ROS.

**3. Find the port** (Linux / WSL terminal). The Black Pill shows up as `ttyACM`, not `ttyUSB`:
```bash
ls /dev/ttyACM*                                   # usually /dev/ttyACM0
sudo usermod -aG dialout $USER                    # once, then log out and back in
```
> **WSL users:** Windows owns USB. In an *admin* PowerShell:
> `usbipd list` → `usbipd bind --busid <id>` → `usbipd attach --wsl --busid <id>`.
> Do this **after** uploading: while it's attached to WSL, the Arduino IDE can't see the board.

**4. Build and start the bridge** (Terminal 1):
```bash
cd ~/ros2-teaching-humble                         # wherever you cloned the repo
colcon build --packages-select mcu_bridge && source install/setup.bash
ros2 launch mcu_bridge bridge.launch.py port:=/dev/ttyACM0
```

**5. Drive with the keyboard** (Terminal 2, `source install/setup.bash` first):
```bash
ros2 run mcu_bridge keyboard_teleop
```
| Key | Motors |
|---|---|
| `w` | both forward |
| `x` | both backward |
| `a` / `d` | opposite ways (that's how a robot turns) |
| `s` or space | stop |
| `q` / `z` | faster / slower |

**6. Drive with no keyboard at all** (Terminal 2, stop teleop first). This is what *your own node* will do:
```bash
# 0.25 m/s forward = half speed (max_wheel_speed is 0.5 in bridge.yaml). -r 10 = send 10 times a second
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.25}}"
```
Press Ctrl+C. The motors stop about half a second later. Nobody sent "stop": the **messages stopped coming**,
so the bridge and then the board's watchdog stopped them. Now try `-r 1` (one message a second). The motor stutters on and off. Why?
(The bridge gives up after 0.5 s of silence, so every message only lasts half a second.)

**7. Look inside** (Terminal 3):
```bash
ros2 topic echo /cmd_vel                          # what the brain asked for
ros2 node info /mcu_bridge                        # who it listens to and talks to
ros2 run rqt_graph rqt_graph                      # the diagram in section 5, live
```

*Ask the class:* we just swapped the Serial Monitor for ROS. Which line of motor code changed?
(None. `Motor.h` does the same `digitalWrite` + `analogWrite` as sketch 02.)

---

## 5. So why do we need ROS at all?

The motor spins fine without ROS. So ask the class: **what is ROS for?**

**The board is the muscle. ROS is the brain.** The Black Pill is great at one job: turning a number into
PWM, fast, forever. It is bad at everything else a robot needs: cameras, maps, planning, a joystick
over Wi-Fi, showing the robot in RViz. ROS runs on the PC (or a Raspberry Pi) and does those jobs.

### What changes when ROS gives the orders

| Without ROS (today) | With ROS |
|---|---|
| You type `f` and `5` | Any node sends a speed on `/cmd_vel` |
| Only the keyboard can drive | Keyboard, joystick, phone, your own code, or Nav2: **the motor code never changes** |
| "Speed 5" means nothing in real life | `/cmd_vel` says **0.2 m/s**. The bridge turns metres per second into PWM |
| One motor at a time | "Go forward and turn left" becomes left/right wheel speeds by itself |
| You can't see what's happening | `ros2 topic echo`, `rqt_plot`, `ros2 bag record`: watch, graph and replay every command |
| Cable pulled = motor keeps going | Watchdog: no message for 0.5 s → motors stop |

### The one idea to remember: swap the boss, keep the motor

```
 keyboard_teleop ─┐
 joystick node   ─┼──► /cmd_vel ──► mcu_bridge ──"M 0.5 0.5"──► Black Pill ──► TB6612 ──► N20
 your AI / Nav2  ─┘
```

Everything left of `/cmd_vel` can be replaced without touching the board. Everything right of it can be
replaced (Uno → ESP32 → Black Pill, TT motor → N20) without touching the brain. That's the whole point:
**a clear line between "deciding" and "doing"**, so ten students can work on ten parts at once.

### How today connects to ROS
`04_serial_control` already is a tiny version of the ROS setup. You are the node, the Serial Monitor is the
topic, the letters are the message. Class 02's `mcu_bridge` does the same job with `M <left> <right>`
instead of `f` and `5`. In **step 6** we removed the human, and a ROS node typed for us.

### For the Defender specifically
- **Drive:** six wheels, but the brain only says "0.3 m/s, turn a bit". ROS splits that into wheel speeds.
- **Shooter:** a ROS **service** like `/fire` could spin up the two flywheels from sketch 05, wait, and spin down.
  Any node (a button, a camera that sees a target) can ask for a shot.
- **The same URDF from class 03** tells RViz where each wheel is, so the robot on screen moves like the real one.

*Ask the class:* if the team switches from N20 to bigger motors next month, which files change?
(Only the firmware pins and `MIN_PWM`. Not a single ROS node.)

---

## 6. Exercises

1. **Brake vs coast.** In `02_forward_backward`, write a `brake()` that sets both AIN pins HIGH. Compare how fast
   the motor stops with `stopMotor()`.
2. **Timed shot.** In `05_two_motors`, add a key `x` that spins up, waits 1 s, then spins down. That's one shot.
3. **Potentiometer throttle.** Put a 10 kΩ pot on PA0 (3V3, PA0, GND). Use `analogRead(PA0)` (0–1023) to set speed.
4. **Watchdog.** In `04_serial_control`, stop the motor if no key arrives for 3 s. Why does `mcu_bridge` have one?
5. **Encoder (if your N20 has the 6-wire encoder).** Wire C1 to PB0 and count pulses with `attachInterrupt`.
   Print the pulses per second. Now you can measure speed instead of guessing it.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Upload says `No DFU capable USB device available` | Do the BOOT0 / NRST dance again; try another USB-C cable (data, not charge-only) |
| Upload says `STM32CubeProgrammer not found` | Install it, then restart the Arduino IDE |
| No COM port after upload | USB support must be **CDC (generic 'Serial'...)**; press NRST |
| Serial Monitor is empty | Press NRST, then reopen the Serial Monitor quickly; check 115200 |
| Motor hums but doesn't turn | Speed below `MIN_PWM`, or battery too weak |
| Motor does nothing at all | STBY not HIGH; VM not connected; **no common GND** |
| Board resets when the motor starts | Motor is powered from the board, or battery too small. Use a separate battery |
| Only spins one way | One of AIN1 / AIN2 isn't connected |
| Driver gets hot | Motor stalled or voltage too high for the N20; check the rating |
| `cannot open /dev/ttyACM0 ... Permission denied` | `dialout` group (step 6), then log out and back in |
| `cannot open ... Device or resource busy` | Close the Arduino Serial Monitor |
| No `/dev/ttyACM0` at all | Press NRST after uploading; WSL: `usbipd attach` again (it detaches on every reset/upload) |
| Bridge runs, `w` does nothing | Is the bridge firmware flashed (not a class 04 sketch)? Check `ros2 topic echo /cmd_vel` shows messages |
| Motor spins the wrong way on `w` | Set `LEFT_INVERTED` / `RIGHT_INVERTED` in `config.h` |
