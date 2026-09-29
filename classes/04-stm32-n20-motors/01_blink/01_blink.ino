// 01_blink.ino - is the Black Pill alive and can we upload to it?
//
// No motor yet. If the small blue LED blinks and the Serial Monitor prints
// "tick", your IDE, board settings and USB cable are all good.
//
// The Black Pill's LED is on PC13 and is "active low":
// writing LOW turns it ON, writing HIGH turns it OFF.

#define LED_PIN PC13

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);  // over USB; the number doesn't matter for USB CDC
}

void loop() {
  digitalWrite(LED_PIN, LOW);   // on
  Serial.println("tick");
  delay(500);
  digitalWrite(LED_PIN, HIGH);  // off
  delay(500);
}
