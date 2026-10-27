// VL53L0X ToF sensors on one I2C bus (GP16 SDA, GP17 SCL). They all start at address 0x29,
// so each has its XSHUT pin: woken one at a time, each gets its own address (0x30 + index).
// One that does not answer stays off (XSHUT low) and is tried again every 2 s, so a sensor
// plugged in later shows up alone. Readings are taken only when one is ready: no waiting.
#pragma once

#include <Arduino.h>
#include <VL53L0X.h>
#include <Wire.h>

#include "Readings.h"

namespace tof {

constexpr uint8_t SDA_PIN = 16, SCL_PIN = 17;
constexpr int16_t MAX_MM = 1200;
constexpr int FAILS_TO_LOSE = 3;
constexpr uint32_t RETRY_MS = 2000;
constexpr uint8_t RESULT_INTERRUPT_STATUS = 0x13;

VL53L0X dev[MAX_SENSORS];
int fails[MAX_SENSORS];
uint32_t lastRetry = 0;

void off(int i) {
  digitalWrite(cfg[i].a, LOW);
  lost(i);
}

// Wake sensor i alone at 0x29 and move it to its own address
bool wake(int i) {
  digitalWrite(cfg[i].a, HIGH);
  delay(2);
  dev[i] = VL53L0X();
  dev[i].setBus(&Wire);
  dev[i].setTimeout(30);
  if (!dev[i].init()) {
    off(i);
    return false;
  }
  dev[i].setAddress(0x30 + i);
  dev[i].startContinuous();
  fails[i] = 0;
  report(i, -1);
  reading[i].fresh = false;     // answers, but no distance yet
  return true;
}

void setup() {
  Wire.setSDA(SDA_PIN);
  Wire.setSCL(SCL_PIN);
  Wire.setClock(100000);
  Wire.setTimeout(10, true);
  Wire.begin();
}

void begin() {
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V') continue;
    pinMode(cfg[i].a, OUTPUT);
    digitalWrite(cfg[i].a, LOW);
    lost(i);
  }
  delay(10);
  for (int i = 0; i < nSensors; i++)
    if (cfg[i].type == 'V') wake(i);
  lastRetry = millis();
}

void loop() {
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V' || !reading[i].answers) continue;
    uint8_t ready = dev[i].readReg(RESULT_INTERRUPT_STATUS) & 0x07;
    if (dev[i].last_status != 0) {
      if (++fails[i] >= FAILS_TO_LOSE) off(i);
      continue;
    }
    if (!ready) continue;
    uint16_t mm = dev[i].readRangeContinuousMillimeters();
    if (dev[i].timeoutOccurred() || dev[i].last_status != 0) {
      if (++fails[i] >= FAILS_TO_LOSE) off(i);
      continue;
    }
    fails[i] = 0;
    report(i, mm > MAX_MM ? -1 : (int16_t)mm);
  }
  if (millis() - lastRetry >= RETRY_MS) {
    lastRetry = millis();
    for (int i = 0; i < nSensors; i++)
      if (cfg[i].type == 'V' && !reading[i].answers) wake(i);
  }
}

}  // namespace tof
