// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The sensors the Pi sends in "CFG V:2 S:10:11 ...": one item per sensor, its index is its
// place in the line. Plain C++ (no Arduino), so test/test_config.cpp runs on any computer.
#pragma once

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

constexpr int MAX_SENSORS = 12;
constexpr int MAX_GPIO = 28;
// The VL53L0X's I2C (GP16 SDA, GP17 SCL), the Pico's own (GP23-25, GP25 = LED) and the
// carrier board's status LEDs (GP0, GP1, GP6-9, GP22, GP27, GP28) and display button (GP26)
constexpr uint8_t RESERVED[] = {0, 1, 6, 7, 8, 9, 16, 17, 22, 23, 24, 25, 26, 27, 28};

struct SensorCfg {
  char type;   // 'V' = VL53L0X, 'S' = HC-SR04
  uint8_t a;   // V: XSHUT; S: TRIG
  uint8_t b;   // S: ECHO; 0 for V
};

// A pin number 0..MAX_GPIO at *p; moves p past it. False if there is none.
inline bool readPin(const char*& p, uint8_t* pin) {
  if (*p < '0' || *p > '9') return false;
  char* end;
  long v = strtol(p, &end, 10);
  if (v > MAX_GPIO || end - p > 2) return false;
  *pin = (uint8_t)v;
  p = end;
  return true;
}

// args = what follows "CFG". nullptr if it is good (out[0..*n-1] filled), else why not
// (the protocol's exact words); after an error *n is 0.
inline const char* parseCfg(const char* args, SensorCfg* out, int* n) {
  static char why[24];
  *n = 0;
  int count = 0;
  const char* p = args;
  while (true) {
    while (*p == ' ') p++;
    if (!*p) break;
    if (count == MAX_SENSORS) return "too many";
    SensorCfg s = {*p, 0, 0};
    bool ok = (s.type == 'V' || s.type == 'S') && p[1] == ':';
    if (ok) {
      p += 2;
      ok = readPin(p, &s.a);
      if (ok && s.type == 'S') ok = *p == ':' && readPin(++p, &s.b);
      ok = ok && (*p == ' ' || !*p);
    }
    if (!ok) {
      snprintf(why, sizeof why, "bad item %d", count);
      return why;
    }
    out[count++] = s;
  }
  for (int i = 0; i < count; i++) {
    uint8_t pins[2] = {out[i].a, out[i].b};
    for (int k = 0; k < (out[i].type == 'S' ? 2 : 1); k++) {
      for (uint8_t r : RESERVED) {
        if (pins[k] == r) {
          snprintf(why, sizeof why, "pin %d reserved", r);
          return why;
        }
      }
      for (int j = 0; j <= i; j++) {
        uint8_t other[2] = {out[j].a, out[j].b};
        int m = out[j].type == 'S' ? 2 : 1;
        for (int q = 0; q < m; q++) {
          if ((j < i || q < k) && other[q] == pins[k]) {
            snprintf(why, sizeof why, "pin %d twice", pins[k]);
            return why;
          }
        }
      }
    }
  }
  *n = count;
  return nullptr;
}
