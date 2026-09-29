// config.h - every pin and number you might need to change, in one place.
#pragma once

// ---- Serial link to the PC ------------------------------------------------
#define BAUD 115200  // must match 'baud' in src/mcu_bridge/config/bridge.yaml
                     // (the Black Pill's USB serial ignores it, any value works)

// Stop the motors if no "M" command arrives for this long. The bridge sends
// 20 per second, so this only fires when the PC, cable or bridge has died.
#define WATCHDOG_MS 500

// Cheap yellow TT gear motors just hum below about this PWM value.
// Raise it if a small command does not start the wheels turning.
#define MIN_PWM 60

// Flip a motor's direction in software instead of re-soldering its wires.
#define LEFT_INVERTED false
#define RIGHT_INVERTED false

#if defined(ESP32)
// ---- ESP32 DevKit ---------------------------------------------------------
// Motor driver: L298N (remove the ENA/ENB jumpers) or TB6612FNG.
#define LEFT_PWM 25
#define LEFT_IN1 26
#define LEFT_IN2 27
#define RIGHT_PWM 32
#define RIGHT_IN1 33
#define RIGHT_IN2 13

// Sensors
#define LDR_PIN 34         // ADC1 pin; LDR + 10k divider between 3.3V and GND
#define SONAR_TRIG_PIN 18
#define SONAR_ECHO_PIN 19  // HC-SR04 echo is 5 V: use a 1k/2k divider!
// MPU6050: SDA = 21, SCL = 22 (the ESP32 default I2C pins)

#elif defined(ARDUINO_ARCH_STM32)
// ---- STM32 Black Pill (F411 / F401) ---------------------------------------
// Same wiring as classes/04-stm32-n20-motors. Driver: TB6612FNG.
// "Left" is motor A, "right" is motor B.
#define LEFT_PWM PA8
#define LEFT_IN1 PB12
#define LEFT_IN2 PB13
#define RIGHT_PWM PB6
#define RIGHT_IN1 PB15
#define RIGHT_IN2 PA10
#define MOTOR_STBY_PIN PB14  // TB6612 standby: the sketch holds it HIGH
#define PWM_FREQUENCY 20000  // above hearing, so the N20s don't whine

// Sensors (leave them unwired if you like; the topics just show junk)
#define LDR_PIN PA0        // LDR + 10k divider between 3.3V and GND
#define SONAR_TRIG_PIN PA1
#define SONAR_ECHO_PIN PA2  // HC-SR04 echo is 5 V: use a 1k/2k divider to be safe
// MPU6050: SDA = PB7, SCL = PB6. PB6 is motor B's PWM here, so move one of them.

#else
// ---- Arduino Uno / Nano ---------------------------------------------------
#define LEFT_PWM 5  // PWM pins on an Uno: 3, 5, 6, 9, 10, 11
#define LEFT_IN1 7
#define LEFT_IN2 8
#define RIGHT_PWM 6
#define RIGHT_IN1 11
#define RIGHT_IN2 12

#define LDR_PIN A0
#define SONAR_TRIG_PIN 2
#define SONAR_ECHO_PIN 3  // 5 V board, no divider needed
// MPU6050: SDA = A4, SCL = A5
#endif
