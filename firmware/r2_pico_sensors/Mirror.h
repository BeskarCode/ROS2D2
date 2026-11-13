// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The board mirror for the web console (protocol 3). While the Pi keeps asking (MIR 1, renewed
// every 2 s; off on its own 5 s after the last one), the Pico sends:
//   LED <10 digits 0/1>  each connector LED's level, VL1..US5, then the Pico's own green LED:
//                        when one changes, and every second
//   FB <base64>          the display's picture (8 SSD1306 pages, 1024 bytes) when it changed,
//                        at most every 200 ms; FB off once when the display goes off
//   BTN short|long       the physical button was pressed (long = held until the display went off)
// and takes PRESS short|long, which goes the same way as the button.
// Plain C++ (no Arduino): test/test_mirror.cpp runs anywhere.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace mirror {

constexpr uint32_t EXPIRE_MS = 5000, FB_MIN_MS = 200, LED_EVERY_MS = 1000;
constexpr size_t FB_BYTES = 1024;

struct State {
  bool on = false;
  uint32_t until = 0;
  uint16_t ledsSent = 0xFFFF;     // none sent yet
  uint32_t ledsAt = 0;
  uint32_t fbAt = 0;
  uint32_t fbHash = 0;
  bool fbSent = false;            // a picture went out since the display came on
  bool fbOff = true;              // FB off already sent (or nothing sent yet)
};

inline void request(State& s, bool on, uint32_t now) {
  s.on = on;
  s.until = now + EXPIRE_MS;
  if (on) {                        // whoever asks gets everything again
    s.ledsSent = 0xFFFF;
    s.fbSent = false;
    s.fbOff = false;
  }
}

inline bool active(const State& s, uint32_t now) { return s.on && (int32_t)(s.until - now) > 0; }

inline size_t base64(const uint8_t* in, size_t len, char* out) {
  static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  size_t o = 0;
  for (size_t i = 0; i < len; i += 3) {
    uint32_t v = (uint32_t)in[i] << 16;
    if (i + 1 < len) v |= (uint32_t)in[i + 1] << 8;
    if (i + 2 < len) v |= in[i + 2];
    out[o++] = T[(v >> 18) & 63];
    out[o++] = T[(v >> 12) & 63];
    out[o++] = i + 1 < len ? T[(v >> 6) & 63] : '=';
    out[o++] = i + 2 < len ? T[v & 63] : '=';
  }
  out[o] = 0;
  return o;
}

// levels: bit 0 = VL1 ... bit 8 = US5, bit 9 = the Pico's own LED (GP25)
inline bool ledLine(State& s, uint16_t levels, uint32_t now, char* out, size_t n) {
  if (levels == s.ledsSent && now - s.ledsAt < LED_EVERY_MS) return false;
  s.ledsSent = levels;
  s.ledsAt = now;
  char d[11];
  for (int i = 0; i < 10; i++) d[i] = (levels >> i) & 1 ? '1' : '0';
  d[10] = 0;
  snprintf(out, n, "LED %s", d);
  return true;
}

inline uint32_t fnv1a(const uint8_t* p, size_t len) {
  uint32_t h = 2166136261u;
  for (size_t i = 0; i < len; i++) h = (h ^ p[i]) * 16777619u;
  return h;
}

// out must hold 3 + 1368 + 1 characters
inline bool fbLine(State& s, const uint8_t* pages, bool displayOn, uint32_t now, char* out, size_t n) {
  if (!displayOn) {
    if (s.fbOff) return false;
    s.fbOff = true;
    s.fbSent = false;
    snprintf(out, n, "FB off");
    return true;
  }
  if (n < 3 + 1368 + 1) return false;
  uint32_t h = fnv1a(pages, FB_BYTES);
  if (s.fbSent && h == s.fbHash) return false;
  if (s.fbSent && now - s.fbAt < FB_MIN_MS) return false;
  s.fbHash = h;
  s.fbAt = now;
  s.fbSent = true;
  s.fbOff = false;
  memcpy(out, "FB ", 3);
  base64(pages, FB_BYTES, out + 3);
  return true;
}

enum class Press { None, Short, Long };

inline Press parsePress(const char* args) {
  if (strcmp(args, "short") == 0) return Press::Short;
  if (strcmp(args, "long") == 0) return Press::Long;
  return Press::None;
}

}  // namespace mirror
