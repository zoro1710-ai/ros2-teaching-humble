// SensorAnalog.h - any sensor that is just a voltage on one pin.
// LDR, potentiometer, soil moisture, flex sensor, MQ gas sensor, sound level...
// Sends the raw reading: 0..1023 on an Uno, 0..4095 on an ESP32.
#pragma once
#include "Sensor.h"

class SensorAnalog : public Sensor {
 public:
  // type is free text ("light", "moisture", ...), so the same class can be
  // reused for many different sensors.
  SensorAnalog(const char* type, const char* name, uint16_t periodMs, uint8_t pin)
      : Sensor(type, name, periodMs), pin_(pin) {}

  void begin() override {
    pinMode(pin_, INPUT);
  }

  uint8_t read(float* values) override {
    values[0] = analogRead(pin_);
    return 1;
  }

 private:
  uint8_t pin_;
};
