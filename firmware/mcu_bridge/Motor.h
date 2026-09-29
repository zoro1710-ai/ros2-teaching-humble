// Motor.h - one DC motor on an L298N or TB6612FNG channel.
//
// Each channel uses three pins:
//   PWM        how hard to push (speed)
//   IN1, IN2   direction: HIGH/LOW = forward, LOW/HIGH = backward,
//              LOW/LOW = coast
#pragma once
#include <Arduino.h>
#include "config.h"

class Motor {
 public:
  Motor(uint8_t pwmPin, uint8_t in1Pin, uint8_t in2Pin, bool inverted)
      : pwm_(pwmPin), in1_(in1Pin), in2_(in2Pin), inverted_(inverted) {}

  void begin() {
    pinMode(pwm_, OUTPUT);
    pinMode(in1_, OUTPUT);
    pinMode(in2_, OUTPUT);
    set(0);
  }

  // command: -1.0 = full backward, 0 = stop, 1.0 = full forward.
  void set(float command) {
    if (inverted_) command = -command;
    command = constrain(command, -1.0f, 1.0f);

    // Tiny commands are treated as stop, so the motor doesn't just buzz.
    const float DEADBAND = 0.02f;
    int pwm = 0;
    if (fabs(command) > DEADBAND) {
      // Map 0..1 onto MIN_PWM..255, the range where the motor actually turns.
      pwm = MIN_PWM + (int)(fabs(command) * (255 - MIN_PWM));
    }

    digitalWrite(in1_, command > DEADBAND ? HIGH : LOW);
    digitalWrite(in2_, command < -DEADBAND ? HIGH : LOW);
    analogWrite(pwm_, pwm);
  }

 private:
  uint8_t pwm_;
  uint8_t in1_;
  uint8_t in2_;
  bool inverted_;
};
