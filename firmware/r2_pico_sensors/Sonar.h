// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// HC-SR04s, one at a time (so they do not hear each other's ping): a 10 us TRIG pulse, then
// the ECHO edges are timed by an interrupt for up to 40 ms. Nothing waits: loop() looks at
// the clock. ECHO has a pull-down, so an unwired one never rises and becomes 'N'.
// A lost one (FAILS_TO_LOSE misses in a row) is skipped and tried again once a second
// (SonarRing.h), so a sensor in the config but not plugged in no longer slows the others down.
#pragma once

#include <Arduino.h>

#include "Measure.h"
#include "Readings.h"
#include "SonarRing.h"

namespace sonar {

constexpr uint32_t WINDOW_US = 40000;   // the HC-SR04 holds ECHO up to ~38 ms with no echo
constexpr int FAILS_TO_LOSE = 3;

int ring[MAX_SENSORS];      // sensor indexes that are HC-SR04s
int nRing = 0;
int last = -1;              // ring place that pinged last
bool busy = false;          // a ping is out, waiting for its echo
int fails[MAX_SENSORS];
uint32_t lastTry[MAX_SENSORS];   // by ring place, millis() of its last ping
uint32_t t0 = 0;
volatile uint8_t echoPin = 0;
Echo echo;

void onEcho() { echoEdge(echo, digitalRead(echoPin), micros()); }

void stop() {
  if (busy) detachInterrupt(cfg[ring[last]].b);
  busy = false;
  last = -1;
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
    lastTry[nRing] = 0;
    ring[nRing++] = i;
  }
}

void ping(uint32_t now) {
  const SensorCfg& s = cfg[ring[last]];
  echoPin = s.b;
  echo = Echo();
  attachInterrupt(digitalPinToInterrupt(s.b), onEcho, CHANGE);
  digitalWrite(s.a, HIGH);
  delayMicroseconds(10);
  digitalWrite(s.a, LOW);
  t0 = now;
}

void finish() {
  int i = ring[last];
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
  if (busy && now - t0 < WINDOW_US) return;
  if (busy) {
    finish();
    busy = false;
  }
  bool gone[MAX_SENSORS];
  for (int k = 0; k < nRing; k++) gone[k] = fails[ring[k]] >= FAILS_TO_LOSE;
  uint32_t ms = millis();
  int next = nextTurn(last, nRing, gone, lastTry, ms);
  if (next < 0) return;          // every one lost and none due for a retry yet
  last = next;
  lastTry[next] = ms;
  busy = true;
  ping(now);
}

}  // namespace sonar
