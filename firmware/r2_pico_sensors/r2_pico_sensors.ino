// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_pico_sensors: R2's distance sensors (VL53L0X, HC-SR04) on a Raspberry Pi Pico 2,
// read for the Pi 4 over USB serial. The Pi sends the sensors and their pins (CFG); the Pico
// measures and answers with text lines. Protocol and wiring: README.md.
// Core 0 measures and talks to the Pi; core 1 runs the carrier board's display, button and
// LEDs (Display.h), which only read what core 0 measured.
#include <Arduino.h>
#include <pico/mutex.h>

#include "Config.h"
#include "Readings.h"
#include "Sonar.h"
#include "Tof.h"
#include "Display.h"

#define FW_VERSION "0.1.0"

constexpr uint8_t LED = LED_BUILTIN;   // GP25 on the Pico 2
constexpr uint32_t HB_MS = 1000, R_MS = 50, FLICKER_MS = 30;
constexpr size_t LINE_MAX = 200;

SensorCfg cfg[MAX_SENSORS];
Reading reading[MAX_SENSORS];
int nSensors = 0;
bool configured = false;

// The I2C bus is shared by the VL53L0X (core 0) and the display (core 1). Initialised before
// either setup() runs.
mutex_t i2cLock;
static struct I2cLockInit {
  I2cLockInit() { mutex_init(&i2cLock); }
} i2cLockInit;

char line[LINE_MAX + 1];
size_t lineLen = 0;
bool tooLong = false;
uint32_t lastHb = 0, lastR = 0, flickerUntil = 0;

// Leave the pins of the last CFG quiet: XSHUT low keeps a VL53L0X off (its board pulls it up)
void releasePins() {
  sonar::stop();
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type == 'V') {
      digitalWrite(cfg[i].a, LOW);
    } else {
      pinMode(cfg[i].a, INPUT);
      pinMode(cfg[i].b, INPUT);
    }
    lost(i);
  }
}

void onCfg(const char* args) {
  SensorCfg next[MAX_SENSORS];
  int n = 0;
  const char* err = parseCfg(args, next, &n);
  releasePins();
  nSensors = 0;
  configured = false;
  if (err) {
    Serial.printf("CFG ERR %s\n", err);
    return;
  }
  for (int i = 0; i < n; i++) {
    cfg[i] = next[i];
    reading[i] = Reading();
  }
  nSensors = n;
  configured = true;
  tof::begin();
  sonar::begin();
  Serial.printf("CFG OK %d\n", n);
}

void onLine(const char* l) {
  if (strcmp(l, "HELLO") == 0) {
    Serial.println("PICO r2_pico_sensors " FW_VERSION " proto 1");
  } else if (strcmp(l, "CFG") == 0 || strncmp(l, "CFG ", 4) == 0) {
    onCfg(l + 3);
  } else if (strcmp(l, "BOOT") == 0) {
    Serial.flush();
    delay(50);
    rp2040.rebootToBootloader();
  } else if (*l) {
    Serial.println("ERR unknown");
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line[lineLen] = 0;
      if (tooLong) Serial.println("ERR too long");
      else onLine(line);
      lineLen = 0;
      tooLong = false;
    } else if (lineLen < LINE_MAX) {
      line[lineLen++] = c;
    } else {
      tooLong = true;
    }
  }
}

void sendHeartbeat(uint32_t now) {
  Serial.printf("HB %lu ", (unsigned long)now);
  if (!configured) {
    Serial.println("-");
    return;
  }
  char states[MAX_SENSORS + 1];
  for (int i = 0; i < nSensors; i++) states[i] = reading[i].answers ? 'O' : 'N';
  states[nSensors] = 0;
  Serial.println(states);
}

void sendReadings(uint32_t now) {
  char out[MAX_SENSORS * 9 + 4] = "R";
  size_t len = 1;
  for (int i = 0; i < nSensors; i++) {
    if (!reading[i].fresh || !reading[i].answers) continue;
    len += snprintf(out + len, sizeof out - len, " %d:%d", i, reading[i].mm);
    reading[i].fresh = false;
  }
  if (len == 1) return;
  Serial.println(out);
  flickerUntil = now + FLICKER_MS;
}

// Slow blink: waiting for the Pi's CFG. On, with a short flicker per R line: measuring.
void led(uint32_t now) {
  bool on = configured ? (int32_t)(now - flickerUntil) >= 0 : now % 1000 < 200;
  digitalWrite(LED, on);
}

// Wokwi (wokwi/README.md) emulates only one core and has no Pi: there the display runs on core 0
// and the sketch configures itself, as the Pi would.
#ifdef WOKWI
constexpr char WOKWI_CFG[] = " V:2 V:3 V:4 S:10:11 S:12:13 S:14:15 S:18:19 S:20:21";
#endif

void setup() {
  pinMode(LED, OUTPUT);
  Serial.begin(115200);
  tof::setup();
#ifdef WOKWI
  display::setup();
  onCfg(WOKWI_CFG);
#endif
}

void loop() {
  readSerial();
  if (configured) {
    tof::loop();
    sonar::loop();
  }
  uint32_t now = millis();
  if (now - lastHb >= HB_MS) {
    lastHb = now;
    sendHeartbeat(now);
  }
  if (configured && now - lastR >= R_MS) {
    lastR = now;
    sendReadings(now);
  }
  led(now);
#ifdef WOKWI
  display::loop();
#endif
}

#ifndef WOKWI
// Core 1: the display, its button and the status LEDs
void setup1() { display::setup(); }

void loop1() { display::loop(); }
#endif
