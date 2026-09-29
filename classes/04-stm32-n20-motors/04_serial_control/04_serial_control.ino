// 04_serial_control.ino - drive the N20 from the keyboard in the Serial Monitor.
//
// Same wiring as 02_forward_backward.
// Serial Monitor: 115200, line ending "No line ending" or "Newline" (both work).
//
//   f   forward          b   backward        s   stop
//   0..9  speed (0 = stopped, 9 = full)      ?   print status
//
// Example: type 5 then f  -> half speed forward. Then b -> half speed backward.
//
// Safety: changing direction goes through a short stop first, so the
// gearbox doesn't get slammed from full forward to full backward.

#define PWMA PA8
#define AIN1 PB12
#define AIN2 PB13
#define STBY PB14

const int MIN_PWM = 60;  // below this the N20 only hums (find yours with 03_speed_ramp)

int direction = 0;  // +1 forward, -1 backward, 0 stopped
int level = 5;      // 0..9 from the keyboard

void apply() {
  int pwm = 0;
  if (direction != 0 && level > 0) {
    // Map level 1..9 onto MIN_PWM..255, the range where the motor turns.
    pwm = map(level, 1, 9, MIN_PWM, 255);
  }
  digitalWrite(AIN1, direction > 0 ? HIGH : LOW);
  digitalWrite(AIN2, direction < 0 ? HIGH : LOW);
  analogWrite(PWMA, pwm);
}

void printStatus() {
  const char* dir = direction > 0 ? "FORWARD" : (direction < 0 ? "BACKWARD" : "STOPPED");
  Serial.print(dir);
  Serial.print("  speed ");
  Serial.print(level);
  Serial.println("/9");
}

void changeDirection(int newDirection) {
  if (direction != 0 && newDirection != direction) {
    direction = 0;
    apply();
    delay(200);  // let it spin down before reversing
  }
  direction = newDirection;
  apply();
}

void setup() {
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);
  analogWriteFrequency(20000);  // quiet PWM
  apply();

  Serial.begin(115200);
  delay(1500);  // USB serial needs a moment after reset
  Serial.println("N20 control: f=forward b=backward s=stop 0-9=speed ?=status");
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();

  if (c == 'f' || c == 'F') {
    changeDirection(+1);
  } else if (c == 'b' || c == 'B') {
    changeDirection(-1);
  } else if (c == 's' || c == 'S' || c == ' ') {
    changeDirection(0);
  } else if (c >= '0' && c <= '9') {
    level = c - '0';
    apply();
  } else if (c == '?') {
    // just print below
  } else {
    return;  // ignore newlines and anything else
  }
  printStatus();
}
