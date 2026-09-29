// 05_two_motors.ino - two N20s, like the Defender's shooter flywheels.
//
// The two flywheels must spin in OPPOSITE directions so they pinch the dart
// and throw it forward (the same thing the mimic joint says in the URDF).
//
// Wiring: channel A exactly as in 02_forward_backward, plus channel B:
//   PB6  -> PWMB
//   PB15 -> BIN1
//   PA10 -> BIN2
//   second motor wires -> BO1 / BO2
//
// Serial Monitor, 115200:
//   f  spin up (flywheels on)      s  spin down (off)
//   r  reverse both (unjam a dart) 0..9  speed

#define PWMA PA8
#define AIN1 PB12
#define AIN2 PB13
#define PWMB PB6
#define BIN1 PB15
#define BIN2 PA10
#define STBY PB14

const int MIN_PWM = 60;
const bool RIGHT_INVERTED = true;  // makes the pair spin opposite; flip if yours already do

// One motor = its three pins. set(): -255..255.
struct Motor {
  int pwm, in1, in2;
  bool inverted;

  void begin() {
    pinMode(pwm, OUTPUT);
    pinMode(in1, OUTPUT);
    pinMode(in2, OUTPUT);
    set(0);
  }

  void set(int speed) {
    if (inverted) speed = -speed;
    speed = constrain(speed, -255, 255);
    digitalWrite(in1, speed > 0 ? HIGH : LOW);
    digitalWrite(in2, speed < 0 ? HIGH : LOW);
    analogWrite(pwm, abs(speed));
  }
};

Motor left = {PWMA, AIN1, AIN2, false};
Motor right = {PWMB, BIN1, BIN2, RIGHT_INVERTED};

int current = 0;  // what the motors are doing now, -255..255
int level = 7;    // 0..9 from the keyboard

// Change speed gradually. A flywheel slammed to full speed draws a big
// current spike, which can reset the Black Pill if the supply is weak.
void rampTo(int target) {
  int step = (target > current) ? 5 : -5;
  while (current != target) {
    current += step;
    if ((step > 0 && current > target) || (step < 0 && current < target)) current = target;
    left.set(current);
    right.set(current);
    delay(10);
  }
}

int levelToPwm() {
  return level == 0 ? 0 : map(level, 1, 9, MIN_PWM, 255);
}

void setup() {
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);
  analogWriteFrequency(20000);
  left.begin();
  right.begin();

  Serial.begin(115200);
  delay(1500);
  Serial.println("Flywheels: f=spin up s=stop r=reverse 0-9=speed");
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();

  if (c == 'f') {
    rampTo(levelToPwm());
  } else if (c == 'r') {
    rampTo(0);
    rampTo(-levelToPwm());
  } else if (c == 's') {
    rampTo(0);
  } else if (c >= '0' && c <= '9') {
    level = c - '0';
    if (current != 0) rampTo(current > 0 ? levelToPwm() : -levelToPwm());
  } else {
    return;
  }
  Serial.print("pwm ");
  Serial.print(current);
  Serial.print("   speed ");
  Serial.print(level);
  Serial.println("/9");
}
