// 03_speed_ramp.ino - slowly speed up and slow down, forward then backward.
//
// Same wiring as 02_forward_backward. Watch the Serial Monitor (or the
// Serial Plotter!) and note the number where the motor actually starts
// turning. Below that it just hums. That number is your MIN_PWM.
//
// One function, one number: speed from -255 (full backward) to +255 (full forward).

#define PWMA PA8
#define AIN1 PB12
#define AIN2 PB13
#define STBY PB14

const int STEP = 5;      // change per step
const int STEP_MS = 50;  // time per step -> 0 to full takes about 2.5 s

// speed: -255..255. The sign is the direction, the size is how fast.
void setMotor(int speed) {
  speed = constrain(speed, -255, 255);
  digitalWrite(AIN1, speed > 0 ? HIGH : LOW);
  digitalWrite(AIN2, speed < 0 ? HIGH : LOW);
  analogWrite(PWMA, abs(speed));
}

void setup() {
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);

  // STM32 default PWM is 1 kHz, which makes the motor whine.
  // 20 kHz is above human hearing.
  analogWriteFrequency(20000);
  setMotor(0);

  Serial.begin(115200);
}

void rampTo(int from, int to) {
  int step = (to > from) ? STEP : -STEP;
  for (int s = from; s != to; s += step) {
    setMotor(s);
    Serial.println(s);
    delay(STEP_MS);
  }
  setMotor(to);
}

void loop() {
  rampTo(0, 255);     // speed up forward
  rampTo(255, 0);     // slow down
  delay(500);
  rampTo(0, -255);    // speed up backward
  rampTo(-255, 0);    // slow down
  delay(500);
}
