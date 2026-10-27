// How a raw HC-SR04 echo or VL53L0X result becomes the millimetres sent to the Pi.
// Plain C++ (no Arduino), so test/test_measure.cpp runs on any computer.
// -1 means "answers, nothing in range": the Pi publishes it as infinity, which the navigator
// reads as a clear way. So anything that is a fault must be MEASURE_FAIL, never -1.
#pragma once

#include <stdint.h>

constexpr int16_t MEASURE_FAIL = -2;
constexpr int16_t SONAR_MAX_MM = 3000;
constexpr int16_t TOF_MAX_MM = 1200;
constexpr uint16_t TOF_NO_TARGET = 8190;   // and above: no target (65535 = the read failed)

struct Echo {
  volatile bool rose = false, fell = false;
  volatile uint32_t riseUs = 0, fallUs = 0;
};

// One ECHO edge (from the interrupt). Edges after the echo has ended are noise: ignored.
inline void echoEdge(Echo& e, bool high, uint32_t t) {
  if (e.fell) return;
  if (high) {
    e.riseUs = t;
    e.rose = true;
  } else if (e.rose) {
    e.fallUs = t;
    e.fell = true;
  }
}

// After the listening window: mm, -1 (no echo back in time, or too far), or MEASURE_FAIL
inline int16_t sonarResult(const Echo& e) {
  if (!e.rose) return MEASURE_FAIL;
  if (!e.fell) return -1;
  int32_t mm = (int32_t)(e.fallUs - e.riseUs) * 343 / 2000;
  if (mm < 0) return MEASURE_FAIL;
  return mm > SONAR_MAX_MM ? -1 : (int16_t)mm;
}

inline int16_t tofResult(uint16_t raw) {
  if (raw == 0xFFFF) return MEASURE_FAIL;
  return raw > TOF_MAX_MM ? -1 : (int16_t)raw;
}
