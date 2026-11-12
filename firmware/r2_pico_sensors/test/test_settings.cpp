// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Host test of the board settings the Pi sends (UI, DISP, ID):
//   g++ -std=c++17 -Wall -I. test/test_settings.cpp -o /tmp/s && /tmp/s
#include <cstdio>
#include <cstring>

#include "Settings.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

static void expectUiError(const char* args, const char* want) {
  UiCfg c;
  const char* err = parseUi(args, c);
  char what[120];
  snprintf(what, sizeof what, "UI%s -> %s (got %s)", args, want, err ? err : "OK");
  check(err && strcmp(err, want) == 0, what);
}

int main() {
  UiCfg c;
  check(c.awake_ms == 30000 && c.brightness == 2 && c.leds == LedMode::Auto, "defaults = today's behaviour");

  check(parseUi(" t=60 b=3 led=on", c) == nullptr, "a good UI line");
  check(c.awake_ms == 60000 && c.brightness == 3 && c.leds == LedMode::On, "UI applied");
  check(parseUi(" t=0 b=0 led=err", c) == nullptr && c.awake_ms == 0 && c.leds == LedMode::Errors, "t=0 = never off; err");
  check(parseUi(" led=off t=10", c) == nullptr && c.leds == LedMode::Off && c.awake_ms == 10000 && c.brightness == 0,
        "any order; what is not given stays");
  check(parseUi(" led=conn", c) == nullptr && c.leds == LedMode::Connected, "conn: only the ones measuring");
  check(parseUi(" led=auto t=300", c) == nullptr && c.leds == LedMode::Auto && c.awake_ms == 300000, "auto, 5 min");

  expectUiError(" t=45", "bad t");
  expectUiError(" b=7", "bad b");
  expectUiError(" led=blink", "bad led");
  expectUiError(" x=1", "bad item x=1");
  expectUiError("", "nothing to set");
  UiCfg keep;
  keep.brightness = 1;
  parseUi(" b=1 t=45", keep);
  check(keep.brightness == 1 && keep.awake_ms == 30000, "a bad line changes nothing");

  check(parseConnector("VL1") == 0 && parseConnector("US5") == 8 && parseConnector("US1") == 4, "connector names");
  check(parseConnector("VL0") == -1 && parseConnector("us1") == -1 && parseConnector("") == -1, "not a connector");

  bool on;
  int screen;
  check(parseDisp(" on", on, screen) == nullptr && on && screen == -1, "DISP on = every sensor");
  check(parseDisp(" on all", on, screen) == nullptr && on && screen == -1, "DISP on all");
  check(parseDisp(" on US3", on, screen) == nullptr && on && screen == 6, "DISP on US3");
  check(parseDisp(" off", on, screen) == nullptr && !on, "DISP off");
  check(parseDisp(" on XX9", on, screen) != nullptr, "DISP on a bad connector");
  check(parseDisp(" maybe", on, screen) != nullptr, "DISP rubbish");

  if (failures) return 1;
  printf("settings: all good\n");
  return 0;
}
