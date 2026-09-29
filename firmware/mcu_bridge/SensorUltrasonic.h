// SensorUltrasonic.h - HC-SR04 distance sensor -> sensor_msgs/Range on the PC.
//
// Wiring: VCC -> 5V, GND -> GND, TRIG -> trigPin, ECHO -> echoPin.
// ESP32: ECHO outputs 5 V, which can damage a 3.3 V pin. Put a 1k resistor
// from ECHO to the pin, and a 2k from the pin to GND.
#pragma once
#include "Sensor.h"

class SensorUltrasonic : public Sensor {
 public:
  SensorUltrasonic(const char* name, uint16_t periodMs, uint8_t trigPin, uint8_t echoPin)
      : Sensor("range", name, periodMs), trig_(trigPin), echo_(echoPin) {}

  void begin() override {
    pinMode(trig_, OUTPUT);
    pinMode(echo_, INPUT);
    digitalWrite(trig_, LOW);
  }

  uint8_t read(float* values) override {
    // A 10 microsecond pulse on TRIG sends one ping.
    digitalWrite(trig_, LOW);
    delayMicroseconds(2);
    digitalWrite(trig_, HIGH);
    delayMicroseconds(10);
    digitalWrite(trig_, LOW);

    // ECHO stays HIGH for as long as the sound took to go out and back.
    // Give up after 25 ms (about 4 m): nothing is in range.
    unsigned long us = pulseIn(echo_, HIGH, 25000UL);

    // ROS convention: +infinity means "nothing detected".
    // Sound travels 343 m/s, and the time covers the trip there AND back.
    values[0] = (us == 0) ? INFINITY : us * 343.0f / 2.0f / 1000000.0f;
    return 1;
  }

 private:
  uint8_t trig_;
  uint8_t echo_;
};
