// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// VL53L0X ToF sensors on one I2C bus (GP16 SDA, GP17 SCL). They all start at address 0x29,
// so each has its XSHUT pin: woken one at a time, each gets its own address (0x30 + index).
// One that does not answer stays off (XSHUT low) and is tried again every 2 s, so a sensor
// plugged in later shows up alone. Readings are taken only when one is ready: no waiting.
// A sensor whose XSHUT does not reach the Pico stays on at 0x29 and would be taken for
// another one: while anything answers at 0x29 with every XSHUT low, nobody is woken.
#pragma once

#include <Arduino.h>
#include <VL53L0X.h>
#include <Wire.h>
#include <pico/mutex.h>

#include "Measure.h"
#include "Readings.h"

extern mutex_t i2cLock;     // the display (core 1) shares the bus

// The bus, held for one transfer. In Wokwi (wokwi/README.md) an interrupt (an HC-SR04 ECHO
// edge) landing mid-transfer hangs its emulated I2C for good, so there interrupts wait too.
inline void i2cTake() {
  mutex_enter_blocking(&i2cLock);
#ifdef WOKWI
  noInterrupts();
#endif
}

inline void i2cGive() {
#ifdef WOKWI
  interrupts();
#endif
  mutex_exit(&i2cLock);
}

namespace tof {

constexpr uint8_t SDA_PIN = 16, SCL_PIN = 17;
constexpr int FAILS_TO_LOSE = 3;
constexpr uint32_t RETRY_MS = 2000;
constexpr uint32_t STUCK_MS = 500;      // answers but no reading for this long: restart it
constexpr uint8_t RESULT_INTERRUPT_STATUS = 0x13;
constexpr uint8_t DEFAULT_ADDRESS = 0x29;

VL53L0X dev[MAX_SENSORS];
int fails[MAX_SENSORS];
uint32_t lastReading[MAX_SENSORS];
uint32_t lastRetry = 0;

// Something at 0x29 although every sensor we wake is moved away from it: an XSHUT not wired.
// Never an empty write (beginTransmission + endTransmission): the RP2350 cannot send one, so the
// core bit-bangs it on SDA/SCL, and a VL53L0X already ranging at its own address took that
// address byte (0x52) as data into its SYSTEM_SEQUENCE_CONFIG and never measured again. One
// register index (the model ID) goes through the I2C block like any other transfer.
bool strayAtDefault() {
  Wire.beginTransmission(DEFAULT_ADDRESS);
  Wire.write(0xC0);     // IDENTIFICATION_MODEL_ID
  return Wire.endTransmission() == 0;
}

void off(int i) {
  digitalWrite(cfg[i].a, LOW);
  lost(i);
}

// Wake sensor i alone at 0x29 and move it to its own address
bool wake(int i) {
  if (strayAtDefault()) {     // two would answer together: wait until the wiring is fixed
    lost(i);
    return false;
  }
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
  lastReading[i] = millis();
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

#ifdef WOKWI
// Wokwi has no VL53L0X: the first two configured sweep from 5 cm to past the scale and back (one
// every 9 s, the other every 12 s), the others never answer.
void begin() {}

void loop() {
  int n = 0;
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V' || n >= 2) continue;
    uint32_t period = 9000 + 3000 * n++;
    uint32_t p = millis() % period;
    int32_t mm = 50 + (int32_t)(p < period / 2 ? p : period - p) * 2 * 1400 / period;
    report(i, mm >= TOF_MAX_MM ? -1 : (int16_t)mm);
  }
}
#else
void begin() {
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V') continue;
    pinMode(cfg[i].a, OUTPUT);
    digitalWrite(cfg[i].a, LOW);
    lost(i);
  }
  delay(10);
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V') continue;
    i2cTake();
    wake(i);
    i2cGive();
  }
  lastRetry = millis();
}

// One VL53L0X's turn: take its reading if there is one (called with the I2C lock held)
void readOne(int i) {
  {
    uint8_t ready = dev[i].readReg(RESULT_INTERRUPT_STATUS) & 0x07;
    if (dev[i].last_status != 0) {
      if (++fails[i] >= FAILS_TO_LOSE) off(i);
      return;
    }
    if (!ready) {
      if (millis() - lastReading[i] > STUCK_MS) off(i);     // retried every RETRY_MS
      return;
    }
    int16_t mm = tofResult(dev[i].readRangeContinuousMillimeters());
    if (dev[i].timeoutOccurred() || dev[i].last_status != 0 || mm == MEASURE_FAIL) {
      if (++fails[i] >= FAILS_TO_LOSE) off(i);
      return;
    }
    fails[i] = 0;
    lastReading[i] = millis();
    report(i, mm);
  }
}

// DBG: one line per VL53L0X that answers, its raw result and a few settings
void debug() {
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V' || !reading[i].answers) continue;
    i2cTake();
    uint8_t irq = dev[i].readReg(RESULT_INTERRUPT_STATUS);
    uint8_t rs = dev[i].readReg(0x14);                 // RESULT_RANGE_STATUS
    uint16_t raw = dev[i].readReg16Bit(0x14 + 10);
    uint8_t seq = dev[i].readReg(0x01);                // SYSTEM_SEQUENCE_CONFIG
    uint8_t mode = dev[i].readReg(0x00);               // SYSRANGE_START
    uint16_t lim = dev[i].readReg16Bit(0x44);          // FINAL_RANGE ... MIN_COUNT_RATE_RTN_LIMIT
    uint8_t vcsel = dev[i].readReg(0x50);              // PRE_RANGE_CONFIG_VCSEL_PERIOD
    uint8_t addr = dev[i].readReg(0x8A);               // I2C_SLAVE_DEVICE_ADDRESS
    uint8_t st = dev[i].last_status;
    uint32_t budget = dev[i].getMeasurementTimingBudget();
    i2cGive();
    Serial.printf("DBG %d addr=%02x irq=%02x rs=%02x(st%d) raw=%u seq=%02x mode=%02x lim=%u vcsel=%02x budget=%lu i2c=%d fails=%d\n",
                  i, addr, irq, rs, (rs >> 3) & 0x0F, raw, seq, mode, lim, vcsel, (unsigned long)budget, st,
                  fails[i]);
  }
}

void loop() {
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type != 'V' || !reading[i].answers) continue;
    i2cTake();
    readOne(i);
    i2cGive();
  }
  if (millis() - lastRetry >= RETRY_MS) {
    lastRetry = millis();
    for (int i = 0; i < nSensors; i++) {
      if (cfg[i].type != 'V' || reading[i].answers) continue;
      i2cTake();
      wake(i);
      i2cGive();
    }
  }
}
#endif

}  // namespace tof
