// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Host test of the board mirror (Mirror.h: MIR expiry, LED and FB lines, PRESS) and uiHold:
//   g++ -std=c++17 -Wall -I. test/test_mirror.cpp -o /tmp/m && /tmp/m
#include <cstdio>
#include <cstring>

#include "Board.h"
#include "Mirror.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main() {
  // uiHold: the same as holding the button 3 s
  Ui ui;
  ui.screen = Screen::All;
  uiHold(ui, 5000);
  check(ui.screen == Screen::Off, "uiHold turns the display off");

  // MIR: on for 5 s after the last request
  mirror::State s;
  check(!mirror::active(s, 0), "off at start");
  mirror::request(s, true, 1000);
  check(mirror::active(s, 5999), "on 4.999 s after the request");
  check(!mirror::active(s, 6000), "off 5 s after the request");
  mirror::request(s, true, 4000);
  check(mirror::active(s, 8999), "renewed at 4 s: on until 9 s");
  mirror::request(s, false, 5000);
  check(!mirror::active(s, 5001), "MIR 0: off at once");

  // LED lines: on change, and at least once a second
  char out[1400];
  mirror::request(s, true, 0);
  check(mirror::ledLine(s, 0b000010001, 100, out, sizeof out), "first LED line goes out");
  check(strcmp(out, "LED 1000100000") == 0, "LED digits VL1..US5, then the Pico's own LED");
  check(!mirror::ledLine(s, 0b000010001, 200, out, sizeof out), "same LEDs 100 ms later: nothing");
  check(mirror::ledLine(s, 0b000010001, 1100, out, sizeof out), "same LEDs a second later: again");
  check(mirror::ledLine(s, 0b000010000, 1150, out, sizeof out), "an LED changes: at once");
  check(strcmp(out, "LED 0000100000") == 0, "VL1 off");
  check(mirror::ledLine(s, 0b1000010000, 1160, out, sizeof out), "the Pico's LED changes: at once");
  check(strcmp(out, "LED 0000100001") == 0, "the Pico's LED is the 10th digit");

  // FB lines: on change, at most every 200 ms; FB off once
  uint8_t pages[1024] = {0};
  check(mirror::fbLine(s, pages, true, 1000, out, sizeof out), "first picture goes out");
  check(strncmp(out, "FB AAAA", 7) == 0, "FB in base64");
  check(strlen(out) == 3 + 1368, "1024 bytes = 1368 base64 characters");
  check(!mirror::fbLine(s, pages, true, 1300, out, sizeof out), "same picture: nothing");
  pages[5] = 0xFF;
  check(!mirror::fbLine(s, pages, true, 1100 + 300 - 250, out, sizeof out), "changed but under 200 ms: wait");
  check(mirror::fbLine(s, pages, true, 1550, out, sizeof out), "changed, 200 ms passed: goes out");
  check(mirror::fbLine(s, pages, false, 1600, out, sizeof out), "display off: FB off");
  check(strcmp(out, "FB off") == 0, "FB off text");
  check(!mirror::fbLine(s, pages, false, 2000, out, sizeof out), "FB off only once");
  check(mirror::fbLine(s, pages, true, 2100, out, sizeof out), "on again: the picture goes out");

  // A new request sends everything again
  mirror::request(s, true, 3000);
  check(mirror::ledLine(s, 0b000010000, 3001, out, sizeof out), "after MIR 1 the LEDs go out again");
  check(mirror::fbLine(s, pages, true, 3001, out, sizeof out), "after MIR 1 the picture goes out again");

  // base64
  char b[16];
  mirror::base64((const uint8_t*)"Man", 3, b);
  check(strcmp(b, "TWFu") == 0, "base64 Man");
  mirror::base64((const uint8_t*)"M", 1, b);
  check(strcmp(b, "TQ==") == 0, "base64 M");
  mirror::base64((const uint8_t*)"Ma", 2, b);
  check(strcmp(b, "TWE=") == 0, "base64 Ma");

  // PRESS
  check(mirror::parsePress("short") == mirror::Press::Short, "PRESS short");
  check(mirror::parsePress("long") == mirror::Press::Long, "PRESS long");
  check(mirror::parsePress("x") == mirror::Press::None, "PRESS x");
  check(mirror::parsePress("") == mirror::Press::None, "PRESS empty");
  check(mirror::parsePress("shorter") == mirror::Press::None, "PRESS shorter");

  if (failures) return 1;
  printf("mirror: all passed\n");
  return 0;
}
