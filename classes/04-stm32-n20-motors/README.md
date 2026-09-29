# Class 04: spin an N20 motor with the STM32 Black Pill

Before ROS can drive anything, the board has to drive a motor. Today: one N20 gear motor,
forward and backward, then speed, then the keyboard, then two of them like the Defender's shooter.

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

---

## 5. Exercises

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
