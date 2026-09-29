// SensorMpu6050.h - MPU6050 accelerometer + gyro -> sensor_msgs/Imu on the PC.
// Talks to the chip directly over I2C, so no extra library is needed.
//
// Wiring: VCC -> 3.3V, GND -> GND, SDA/SCL -> the board's I2C pins (config.h).
#pragma once
#include <Wire.h>
#include "Sensor.h"

class SensorMpu6050 : public Sensor {
 public:
  SensorMpu6050(const char* name, uint16_t periodMs, uint8_t address = 0x68)
      : Sensor("imu", name, periodMs), address_(address) {}

  void begin() override {
    Wire.begin();
    // Register 0x6B = power management. Writing 0 wakes the chip up.
    Wire.beginTransmission(address_);
    Wire.write(0x6B);
    Wire.write(0);
    found_ = (Wire.endTransmission() == 0);
    if (!found_) Serial.print("E mpu6050 not found - check SDA/SCL wiring\n");
  }

  uint8_t read(float* values) override {
    if (!found_) return 0;

    // 14 bytes starting at 0x3B: accel XYZ, temperature, gyro XYZ.
    Wire.beginTransmission(address_);
    Wire.write(0x3B);
    if (Wire.endTransmission(false) != 0) return 0;
    if (Wire.requestFrom((int)address_, 14) != 14) return 0;

    int16_t raw[7];
    for (uint8_t i = 0; i < 7; i++) {
      // Two separate reads: C++ does not promise the order of two
      // Wire.read() calls written in one expression.
      uint8_t high = Wire.read();
      uint8_t low = Wire.read();
      raw[i] = (int16_t)((high << 8) | low);
    }

    // Default ranges: +-2 g -> 16384 counts per g, +-250 deg/s -> 131 per deg/s.
    // ROS wants SI units: m/s^2 and rad/s.
    const float G = 9.80665f;
    values[0] = raw[0] / 16384.0f * G;
    values[1] = raw[1] / 16384.0f * G;
    values[2] = raw[2] / 16384.0f * G;
    // raw[3] is the chip temperature - skipped.
    values[3] = raw[4] / 131.0f * DEG_TO_RAD;
    values[4] = raw[5] / 131.0f * DEG_TO_RAD;
    values[5] = raw[6] / 131.0f * DEG_TO_RAD;
    return 6;
  }

 private:
  uint8_t address_;
  bool found_ = false;
};
