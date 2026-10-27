// Host test of the carrier board's connector map and the display's button logic:
//   g++ -std=c++17 -Wall -I. test/test_board.cpp -o /tmp/b && /tmp/b
#include <cstdio>

#include "Board.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main() {
  check(connectorOf({'V', 2, 0}) == 0, "XSHUT GP2 = VL1");
  check(connectorOf({'V', 5, 0}) == 3, "XSHUT GP5 = VL4");
  check(connectorOf({'S', 10, 11}) == 4, "TRIG GP10 = US1");
  check(connectorOf({'S', 14, 15}) == 6, "TRIG GP14 = US3");
  check(connectorOf({'S', 20, 21}) == 8, "TRIG GP20 = US5");
  check(connectorOf({'V', 6, 0}) == -1, "GP6 is no connector");
  check(connectorOf({'S', 11, 12}) == -1, "TRIG GP11 is no connector");
  check(connectorOf({'S', 10, 13}) == -1, "US1 with the wrong ECHO is no connector");

  Ui ui;
  check(ui.screen == Screen::Off, "starts off");
  uiPress(ui, 1000);
  check(ui.screen == Screen::Splash, "first press: the logo");
  uiPress(ui, 1020);
  check(ui.screen == Screen::Splash, "a bounce 20 ms later counts as nothing");
  uiPress(ui, 2000);
  check(ui.screen == Screen::Sensor && ui.shown == 0, "second press: the first connector");
  uiPress(ui, 3000);
  check(ui.shown == 1, "next press: the next connector");
  for (int i = 0; i < 7; i++) uiPress(ui, 4000 + i * 1000);
  check(ui.shown == 8, "up to US5");
  uiPress(ui, 12000);
  check(ui.shown == 0, "after US5, VL1 again");
  uiPress(ui, 13000);
  uiTick(ui, 13000 + AWAKE_MS - 1);
  check(ui.screen == Screen::Sensor, "still on just before 30 s");
  uiTick(ui, 13000 + AWAKE_MS + 1);
  check(ui.screen == Screen::Off, "off 30 s after the last press");
  uiPress(ui, 50000);
  check(ui.screen == Screen::Splash, "wakes to the logo");
  uiPress(ui, 51000);
  check(ui.screen == Screen::Sensor && ui.shown == 1, "then the last connector seen");
  Ui splash;
  uiPress(splash, 100);
  uiTick(splash, 100 + AWAKE_MS + 1);
  check(splash.screen == Screen::Off, "the logo also goes off after 30 s");

  if (failures) return 1;
  printf("all passed\n");
  return 0;
}
