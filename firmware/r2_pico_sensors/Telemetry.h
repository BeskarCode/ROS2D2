// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Telemetry for the console's System tab, only while the Pi asks for it (TM 1): how busy each
// core is, how much of the I2C bus is taken (and how much of it by the display), the longest
// a VL53L0X waited for the bus, readings per second of each sensor. One "T ..." line a second.
// The counting is plain C++ (formatTm is tested on the host: test/test_telemetry.cpp); the
// hooks below it run only on the Pico.
#pragma once

#include <stdint.h>
#include <stdio.h>

#include "Config.h"

struct TmWindow {
  uint32_t busy0_us, busy1_us;     // each core's time doing work (its loop's body)...
  uint32_t wait0_us, wait1_us;     // ...of which this long waiting for the I2C bus
  uint32_t bus_us, disp_us;        // the bus held, and held by the display (core 1)
  uint32_t wait_max_us;            // the longest core 0 (the VL53L0X) waited for the bus
  uint16_t reads[MAX_SENSORS];     // readings of each sensor
};

inline int tmPct(uint32_t part, uint32_t window_us) {
  return window_us ? (int)((part * 100ULL + window_us / 2) / window_us) : 0;
}

// "T c0=<%> c1=<%> bus=<%> disp=<%> wait=<ms> temp=<tenths °C> up=<s> rps=<n>,<n>,..."
// The cores' load leaves out their waits for the bus. Returns the length written.
inline int formatTm(char* out, size_t n, const TmWindow& w, uint32_t window_us, int temp_dc,
                    uint32_t up_s, int nSensors) {
  uint32_t c0 = w.busy0_us > w.wait0_us ? w.busy0_us - w.wait0_us : 0;
  uint32_t c1 = w.busy1_us > w.wait1_us ? w.busy1_us - w.wait1_us : 0;
  int len = snprintf(out, n, "T c0=%d c1=%d bus=%d disp=%d wait=%lu temp=%d up=%lu rps=",
                     tmPct(c0, window_us), tmPct(c1, window_us), tmPct(w.bus_us, window_us),
                     tmPct(w.disp_us, window_us), (unsigned long)((w.wait_max_us + 500) / 1000),
                     temp_dc, (unsigned long)up_s);
  for (int i = 0; i < nSensors && len >= 0 && (size_t)len < n; i++) {
    uint32_t rps = window_us ? (uint32_t)((w.reads[i] * 1000000ULL + window_us / 2) / window_us) : 0;
    len += snprintf(out + len, n - len, i ? ",%lu" : "%lu", (unsigned long)rps);
  }
  if (n) out[n - 1] = 0;
  return len < (int)n ? len : (int)n - 1;
}

#ifdef ARDUINO
#include <Arduino.h>
#include <pico/platform.h>

namespace tele {

inline volatile bool on = false;      // TM 1 / TM 0 from the Pi; off after a restart
inline TmWindow w{};
inline uint32_t windowStart = 0, heldSince = 0;
inline uint8_t holder = 0;

inline void start(uint32_t now_us) {
  w = TmWindow{};
  windowStart = now_us;
}

// called with the I2C lock just taken / about to be given back
inline void tookBus(uint32_t asked_us, uint32_t got_us) {
  if (!on) return;
  holder = get_core_num();
  heldSince = got_us;
  uint32_t waited = got_us - asked_us;
  if (holder == 0) {
    w.wait0_us += waited;
    if (waited > w.wait_max_us) w.wait_max_us = waited;
  } else {
    w.wait1_us += waited;
  }
}

inline void gaveBus(uint32_t now_us) {
  if (!on) return;
  uint32_t held = now_us - heldSince;
  w.bus_us += held;
  if (holder == 1) w.disp_us += held;
}

// A loop turn that took this long did work; an idle turn (nothing to do) takes a few µs.
// Both loops spin all the time, so timing every turn would always say 100 %.
constexpr uint32_t BUSY_MIN_US = 20;

inline void busy(uint32_t us) {
  if (!on || us < BUSY_MIN_US) return;
  if (get_core_num() == 0) w.busy0_us += us; else w.busy1_us += us;
}

inline void read(int i) {
  if (on && i >= 0 && i < MAX_SENSORS) w.reads[i]++;
}

}  // namespace tele
#endif
