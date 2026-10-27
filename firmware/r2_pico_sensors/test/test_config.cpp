// Host test of the CFG parser (no Arduino):
//   g++ -std=c++17 -Wall -I. test/test_config.cpp -o /tmp/t && /tmp/t
#include <cstdio>
#include <cstring>
#include <string>

#include "Config.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

static void expectError(const char* args, const char* why) {
  SensorCfg s[MAX_SENSORS];
  int n = -1;
  const char* err = parseCfg(args, s, &n);
  std::string what = std::string("'") + args + "' -> '" + why + "' (got '" + (err ? err : "ok") + "')";
  check(err && strcmp(err, why) == 0, what.c_str());
}

int main() {
  SensorCfg s[MAX_SENSORS];
  int n = -1;

  check(parseCfg("", s, &n) == nullptr && n == 0, "empty CFG = no sensors");

  n = -1;
  check(parseCfg("V:2 V:3 S:10:11", s, &n) == nullptr && n == 3, "three sensors");
  check(s[0].type == 'V' && s[0].a == 2 && s[0].b == 0, "first is a VL53L0X on 2");
  check(s[1].type == 'V' && s[1].a == 3, "second is a VL53L0X on 3");
  check(s[2].type == 'S' && s[2].a == 10 && s[2].b == 11, "third is a HC-SR04 on 10/11");

  n = -1;
  check(parseCfg("  V:2   S:10:11  ", s, &n) == nullptr && n == 2, "extra spaces are fine");

  expectError("V:16", "pin 16 reserved");
  expectError("S:10:25", "pin 25 reserved");
  expectError("V:2 S:2:3", "pin 2 twice");
  expectError("V:22", "pin 22 reserved");   // the carrier board's LEDs
  expectError("S:26:27", "pin 26 reserved");  // and its button
  expectError("S:10", "bad item 0");
  expectError("X:1", "bad item 0");
  expectError("V:29", "bad item 0");
  expectError("V:2 V:", "bad item 1");
  expectError("V:2x", "bad item 0");
  expectError("V:0 V:1 V:2 V:3 V:4 V:5 V:6 V:7 V:8 V:9 V:10 V:11 V:12", "too many");

  // An error leaves no sensors behind
  n = 5;
  parseCfg("V:16", s, &n);
  check(n == 0, "an error means no sensors");

  if (failures) return 1;
  printf("all passed\n");
  return 0;
}
