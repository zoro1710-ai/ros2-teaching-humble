// 02_forward_backward.ino - one N20 motor: forward, stop, backward, stop, repeat.
//
// Wiring (Black Pill -> TB6612FNG, channel A):
//   PA8  -> PWMA    speed
//   PB12 -> AIN1    direction
//   PB13 -> AIN2    direction
//   PB14 -> STBY    driver on/off (or just tie STBY to 3V3)
//   3V3  -> VCC     driver logic
//   GND  -> GND     SHARE GROUND with the motor battery!
//   Motor battery + -> VM,   motor wires -> AO1 / AO2
//
// How the driver reads the pins:
//   AIN1  AIN2   motor
//   HIGH  LOW    forward
//   LOW   HIGH   backward
//   LOW   LOW    coast (free spin)
//   HIGH  HIGH   brake
// PWMA says how hard: analogWrite 0 = nothing, 255 = full speed.

#define PWMA PA8
#define AIN1 PB12
#define AIN2 PB13
#define STBY PB14

const int SPEED = 180;      // 0..255. Try 100, then 255.
const int RUN_MS = 2000;    // how long to spin each way
const int PAUSE_MS = 1000;  // rest between direction changes (be kind to the gears)

void forward(int speed) {
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  analogWrite(PWMA, speed);
}

void backward(int speed) {
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);
  analogWrite(PWMA, speed);
}

void stopMotor() {
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  analogWrite(PWMA, 0);
}

void setup() {
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);  // wake the driver up
  stopMotor();

  Serial.begin(115200);
}

void loop() {
  Serial.println("forward");
  forward(SPEED);
  delay(RUN_MS);

  Serial.println("stop");
  stopMotor();
  delay(PAUSE_MS);

  Serial.println("backward");
  backward(SPEED);
  delay(RUN_MS);

  Serial.println("stop");
  stopMotor();
  delay(PAUSE_MS);
}
