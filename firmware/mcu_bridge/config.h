// config.h - every pin and number you might need to change, in one place.
#pragma once

// ---- Serial link to the PC ------------------------------------------------
#define BAUD 115200  // must match 'baud' in src/mcu_bridge/config/bridge.yaml

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
