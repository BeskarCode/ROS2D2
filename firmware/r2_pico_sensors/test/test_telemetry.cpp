// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Host test of the telemetry line (TM):
//   g++ -std=c++17 -Wall -I. test/test_telemetry.cpp -o /tmp/t && /tmp/t
#include <cstdio>
#include <cstring>

#include "Telemetry.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main() {
  TmWindow w{};
  // one second: core 0 busy 120 ms, core 1 480 ms; the bus held 510 ms, 460 of them by the
  // display; a VL waited at most 37 ms for it; 20 readings from sensors 0 and 1, none from 2
  w.busy0_us = 120000;
  w.busy1_us = 480000;
  w.bus_us = 510000;
  w.disp_us = 460000;
  w.wait_max_us = 37400;
  w.reads[0] = 20;
  w.reads[1] = 20;
  char out[160];
  int n = formatTm(out, sizeof out, w, 1000000, 312, 3600, 3);
  check(strcmp(out, "T c0=12 c1=48 bus=51 disp=46 wait=37 temp=312 up=3600 rps=20,20,0") == 0, out);
  check(n == (int)strlen(out), "returns the length");

  // a window of 2 s halves the rates; no sensors = empty rps
  n = formatTm(out, sizeof out, w, 2000000, -5, 7, 0);
  check(strcmp(out, "T c0=6 c1=24 bus=26 disp=23 wait=37 temp=-5 up=7 rps=") == 0, out);

  // never past the buffer, always terminated
  char small[20];
  memset(small, 'x', sizeof small);
  formatTm(small, sizeof small, w, 1000000, 312, 3600, 3);
  check(small[sizeof small - 1] == 0, "terminated in a small buffer");

  // a zero window (should not happen) does not divide by zero
  formatTm(out, sizeof out, w, 0, 0, 0, 1);
  check(strncmp(out, "T c0=0 c1=0 bus=0", 17) == 0, out);

  if (failures) return 1;
  printf("telemetry: all good\n");
  return 0;
}
