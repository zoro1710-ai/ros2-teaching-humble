// mcu_bridge.ino - the board half of the sensor + motor boilerplate.
//
// Pairs with the ROS 2 node in src/mcu_bridge. Works on ESP32, Arduino
// Uno/Nano and the STM32 Black Pill with the plain Arduino IDE; no micro-ROS
// or extra libraries.
//
//   board -> PC   S <type> <name> <values...>   every sensor, on its own timer
//   PC -> board   M <left> <right>              wheel commands, -1.0 .. 1.0
//
// Try it without ROS: open the Serial Monitor at 115200 baud, set the line
// ending to "Newline", and type   M 0.5 0.5   (motors run for WATCHDOG_MS).
//
// ADD A SENSOR = the three steps marked (1) (2) (3) below. Nothing else.

#include "config.h"
#include "Motor.h"
#include "Sensor.h"

// (1) Include the sensor classes you use.
#include "SensorAnalog.h"
#include "SensorUltrasonic.h"
// #include "SensorMpu6050.h"

// (2) Create one object per physical sensor: name, how often (ms), pins.
SensorAnalog light("light", "ldr", 100, LDR_PIN);
SensorUltrasonic sonar("front_sonar", 100, SONAR_TRIG_PIN, SONAR_ECHO_PIN);
// SensorMpu6050 imu("imu", 20);

// (3) List them here.
Sensor* SENSORS[] = {&light, &sonar};

const uint8_t SENSOR_COUNT = sizeof(SENSORS) / sizeof(SENSORS[0]);

Motor leftMotor(LEFT_PWM, LEFT_IN1, LEFT_IN2, LEFT_INVERTED);
Motor rightMotor(RIGHT_PWM, RIGHT_IN1, RIGHT_IN2, RIGHT_INVERTED);

uint32_t lastCommandMs = 0;
bool motorsRunning = false;

char line[48];
uint8_t lineLength = 0;

void stopMotors() {
  leftMotor.set(0);
  rightMotor.set(0);
  motorsRunning = false;
}

// Handle one complete line from the PC, e.g. "M 0.500 -0.250".
void handleCommand(char* text) {
  if (text[0] != 'M') {
    Serial.print("E unknown command\n");
    return;
  }
  // strtod instead of sscanf: sscanf cannot read floats on an Uno.
  char* start = text + 1;
  char* end;
  float left = strtod(start, &end);
  if (end == start) return;
  start = end;
  float right = strtod(start, &end);
  if (end == start) return;

  leftMotor.set(left);
  rightMotor.set(right);
  motorsRunning = true;
  lastCommandMs = millis();
}

// Collect characters until a newline, without ever waiting.
void readCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line[lineLength] = '\0';
      if (lineLength > 0) handleCommand(line);
      lineLength = 0;
    } else if (lineLength < sizeof(line) - 1) {
      line[lineLength++] = c;
    } else {
      lineLength = 0;  // too long to be ours: throw it away
    }
  }
}

void setup() {
  Serial.begin(BAUD);
#ifdef MOTOR_STBY_PIN
  pinMode(MOTOR_STBY_PIN, OUTPUT);
  digitalWrite(MOTOR_STBY_PIN, HIGH);  // wake the TB6612 up
#endif
#ifdef PWM_FREQUENCY
  analogWriteFrequency(PWM_FREQUENCY);
#endif
  leftMotor.begin();
  rightMotor.begin();
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) SENSORS[i]->begin();

  Serial.print("I ready with ");
  Serial.print(SENSOR_COUNT);
  Serial.print(" sensors\n");
}

void loop() {
  readCommands();

  // Safety first: no word from the PC recently -> stop.
  if (motorsRunning && millis() - lastCommandMs > WATCHDOG_MS) {
    stopMotors();
    Serial.print("I watchdog: no commands, motors stopped\n");
  }

  for (uint8_t i = 0; i < SENSOR_COUNT; i++) SENSORS[i]->update();
}
