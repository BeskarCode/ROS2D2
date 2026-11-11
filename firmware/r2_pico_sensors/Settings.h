// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The carrier board's settings and actions the Pi sends (the Pico keeps none: the Pi sends them
// again after every CFG):
//   UI t=<s> b=<0-3> led=<auto|on|off|err>   display timeout (10, 30, 60, 300; 0 = never),
//                                            brightness, LED mode; any of them, any order
//   DISP on [all|VL1..US5] / DISP off         the display on (every sensor, or one) or off
//   ID <VL1..US5>                             that connector's LED blinks fast for 5 s
// Plain C++: test/test_settings.cpp runs anywhere.
#pragma once

#include <stdlib.h>
#include <string.h>

#include "Board.h"

struct UiCfg {
  uint32_t awake_ms = AWAKE_MS;
  uint8_t brightness = 2;          // 0-3
  LedMode leds = LedMode::Auto;
};

constexpr uint32_t IDENTIFY_MS = 5000;

// The SSD1306 contrast of each brightness (2 = what it always had)
constexpr uint8_t CONTRAST[4] = {0x08, 0x40, 0xCF, 0xFF};

// "VL1".."US5" -> 0..8, else -1
inline int parseConnector(const char* s) {
  for (int c = 0; c < N_CONN; c++)
    if (strcmp(s, CONN_NAME[c]) == 0) return c;
  return -1;
}

// args = what follows "UI". nullptr if good (out changed), else why not (out untouched)
inline const char* parseUi(const char* args, UiCfg& out) {
  static char err[40];
  UiCfg next = out;
  int n = 0;
  char buf[96];
  strncpy(buf, args, sizeof buf - 1);
  buf[sizeof buf - 1] = 0;
  for (char* item = strtok(buf, " "); item; item = strtok(nullptr, " ")) {
    n++;
    char* eq = strchr(item, '=');
    if (!eq) {
      snprintf(err, sizeof err, "bad item %.20s", item);
      return err;
    }
    *eq = 0;
    const char* v = eq + 1;
    if (strcmp(item, "t") == 0) {
      int s = atoi(v);
      if (!(strcmp(v, "0") == 0 || s == 10 || s == 30 || s == 60 || s == 300)) return "bad t";
      next.awake_ms = (uint32_t)s * 1000;
    } else if (strcmp(item, "b") == 0) {
      if (strlen(v) != 1 || v[0] < '0' || v[0] > '3') return "bad b";
      next.brightness = v[0] - '0';
    } else if (strcmp(item, "led") == 0) {
      if (strcmp(v, "auto") == 0) next.leds = LedMode::Auto;
      else if (strcmp(v, "on") == 0) next.leds = LedMode::On;
      else if (strcmp(v, "off") == 0) next.leds = LedMode::Off;
      else if (strcmp(v, "err") == 0) next.leds = LedMode::Errors;
      else return "bad led";
    } else {
      snprintf(err, sizeof err, "bad item %.10s=%.10s", item, v);
      return err;
    }
  }
  if (!n) return "nothing to set";
  out = next;
  return nullptr;
}

// args = what follows "DISP". screen -1 = every sensor, else the connector
inline const char* parseDisp(const char* args, bool& on, int& screen) {
  while (*args == ' ') args++;
  if (strcmp(args, "off") == 0) {
    on = false;
    return nullptr;
  }
  if (strncmp(args, "on", 2) != 0 || (args[2] && args[2] != ' ')) return "bad DISP";
  const char* what = args + 2;
  while (*what == ' ') what++;
  if (!*what || strcmp(what, "all") == 0) {
    on = true;
    screen = -1;
    return nullptr;
  }
  int c = parseConnector(what);
  if (c < 0) return "bad connector";
  on = true;
  screen = c;
  return nullptr;
}
