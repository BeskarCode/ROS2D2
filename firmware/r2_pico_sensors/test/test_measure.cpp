// Host test of the measuring rules (no Arduino):
//   g++ -std=c++17 -Wall -I. test/test_measure.cpp -o /tmp/m && /tmp/m
#include <cstdio>

#include "Measure.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main() {
  // HC-SR04: an echo of 2332 us is 0.4 m
  Echo e;
  echoEdge(e, true, 1000);
  echoEdge(e, false, 3332);
  check(sonarResult(e) == 399, "2332 us = 399 mm");

  // a glitch (a rising edge after the echo ended) must not change the reading
  echoEdge(e, true, 3362);
  check(sonarResult(e) == 399, "a rising edge after the fall is ignored");

  // rose, never fell within the window: nothing in range
  Echo far;
  echoEdge(far, true, 1000);
  check(sonarResult(far) == -1, "no fall = nothing in range");

  // never rose: the sensor does not answer
  Echo none;
  check(sonarResult(none) == MEASURE_FAIL, "no rise = no answer");

  // beyond 3 m: nothing in range
  Echo beyond;
  echoEdge(beyond, true, 0);
  echoEdge(beyond, false, 20000);
  check(sonarResult(beyond) == -1, "over 3 m = nothing in range");

  // VL53L0X
  check(tofResult(420) == 420, "420 mm");
  check(tofResult(1300) == -1, "over 1.2 m = nothing in range");
  check(tofResult(8190) == -1, "8190 = no target");
  check(tofResult(65535) == MEASURE_FAIL, "65535 = a failed I2C read, never 'nothing in range'");

  if (failures) return 1;
  printf("all passed\n");
  return 0;
}
