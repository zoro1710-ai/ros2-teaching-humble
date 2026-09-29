// SensorTemplate.h - copy me to add a new sensor.
//
//   1. Copy this file to Sensor<YourThing>.h and rename the class.
//   2. Fill in begin() and read().
//   3. In mcu_bridge.ino: #include it, create one object, and add it to
//      the SENSORS list.
//
// That's all. Upload, restart the bridge, and /sensors/<name> appears.
#pragma once
#include "Sensor.h"

class SensorTemplate : public Sensor {
 public:
  // "my_type" -> which ROS message the PC builds (see converters.py).
  //             Unknown words are fine: you get a Float32MultiArray.
  SensorTemplate(const char* name, uint16_t periodMs, uint8_t pin)
      : Sensor("my_type", name, periodMs), pin_(pin) {}

  void begin() override {
    pinMode(pin_, INPUT);
  }

  uint8_t read(float* values) override {
    values[0] = analogRead(pin_);  // first number
    // values[1] = ...;            // add more if your sensor has them
    return 1;                      // how many numbers you filled in
  }

 private:
  uint8_t pin_;
};
