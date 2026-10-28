// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// HC-SR04s, one at a time (so they do not hear each other's ping): a 10 us TRIG pulse, then
// the ECHO edges are timed by an interrupt for up to 40 ms. Nothing waits: loop() looks at
// the clock. ECHO has a pull-down, so an unwired one never rises and becomes 'N'.
#pragma once

#include <Arduino.h>

#include "Measure.h"
#include "Readings.h"

namespace sonar {

constexpr uint32_t WINDOW_US = 40000;   // the HC-SR04 holds ECHO up to ~38 ms with no echo
constexpr int FAILS_TO_LOSE = 3;

int ring[MAX_SENSORS];      // sensor indexes that are HC-SR04s
int nRing = 0;
int turn = -1;              // place in ring of the one pinging now
int fails[MAX_SENSORS];
uint32_t t0 = 0;
volatile uint8_t echoPin = 0;
Echo echo;

void onEcho() { echoEdge(echo, digitalRead(echoPin), micros()); }

void stop() {
  if (turn >= 0) detachInterrupt(cfg[ring[turn]].b);
  turn = -1;
  nRing = 0;
}

void begin() {
  stop();
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'S') continue;
    pinMode(cfg[i].a, OUTPUT);
    digitalWrite(cfg[i].a, LOW);
    pinMode(cfg[i].b, INPUT_PULLDOWN);
    fails[i] = 0;
    ring[nRing++] = i;
  }
}

void ping(uint32_t now) {
  const SensorCfg& s = cfg[ring[turn]];
  echoPin = s.b;
  echo = Echo();
  attachInterrupt(digitalPinToInterrupt(s.b), onEcho, CHANGE);
  digitalWrite(s.a, HIGH);
  delayMicroseconds(10);
  digitalWrite(s.a, LOW);
  t0 = now;
}

void finish() {
  int i = ring[turn];
  detachInterrupt(digitalPinToInterrupt(cfg[i].b));
  int16_t mm = sonarResult(echo);
  if (mm != MEASURE_FAIL) {
    fails[i] = 0;
    report(i, mm);
  } else if (++fails[i] >= FAILS_TO_LOSE) {
    lost(i);
  }
}

void loop() {
  if (!nRing) return;
  uint32_t now = micros();
  if (turn >= 0 && now - t0 < WINDOW_US) return;
  if (turn >= 0) finish();
  turn = (turn + 1) % nRing;
  ping(now);
}

}  // namespace sonar
