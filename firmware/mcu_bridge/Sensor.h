// Sensor.h - the one base class every sensor inherits from.
//
// A sensor only has to answer: "what are your numbers right now?"
// This class handles timing and prints the line the PC understands:
//
//     S <type> <name> <v1> <v2> ...
//
//   type  tells the PC which ROS message to build ("range", "imu",
//         "temperature"). Any other word works too: the PC then publishes
//         a plain Float32MultiArray.
//   name  becomes the topic /sensors/<name> and the frame <name>_link.
//         No spaces. Every sensor needs its own name.
#pragma once
#include <Arduino.h>

const uint8_t MAX_VALUES = 8;

class Sensor {
 public:
  Sensor(const char* type, const char* name, uint16_t periodMs)
      : type_(type), name_(name), periodMs_(periodMs) {}
  virtual ~Sensor() {}

  // Runs once in setup(): pinMode, Wire.begin, ... Optional.
  virtual void begin() {}

  // Put your numbers in values[] and return how many you wrote.
  // Return 0 to skip this turn (sensor not ready, bad reading, ...).
  virtual uint8_t read(float* values) = 0;

  // Called on every loop(). Reads and prints once every periodMs.
  void update() {
    uint32_t now = millis();
    if (now - lastMs_ < periodMs_) return;
    lastMs_ = now;

    float values[MAX_VALUES];
    uint8_t count = read(values);
    if (count == 0) return;

    Serial.print("S ");
    Serial.print(type_);
    Serial.print(' ');
    Serial.print(name_);
    for (uint8_t i = 0; i < count && i < MAX_VALUES; i++) {
      Serial.print(' ');
      Serial.print(values[i], 4);
    }
    Serial.print('\n');
  }

 protected:
  const char* type_;
  const char* name_;

 private:
  uint16_t periodMs_;
  uint32_t lastMs_ = 0;
};
