// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
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
  check(ui.screen == Screen::All, "second press: every sensor at once");
  uiPress(ui, 3000);
  check(ui.screen == Screen::Sensor && ui.shown == 0, "third press: the first connector");
  uiPress(ui, 4000);
  check(ui.shown == 1, "next press: the next connector");
  for (int i = 0; i < 7; i++) uiPress(ui, 5000 + i * 1000);
  check(ui.screen == Screen::Sensor && ui.shown == 8, "up to US5");
  uiPress(ui, 12000);
  check(ui.screen == Screen::All, "after US5, every sensor again");
  uiPress(ui, 13000);
  check(ui.screen == Screen::Sensor && ui.shown == 0, "and then VL1 again");
  uiTick(ui, 13000 + AWAKE_MS - 1);
  check(ui.screen == Screen::Sensor, "still on just before 30 s");
  uiTick(ui, 13000 + AWAKE_MS + 1);
  check(ui.screen == Screen::Off, "off 30 s after the last press");
  uiPress(ui, 50000);
  check(ui.screen == Screen::Splash, "wakes to the logo");
  uiPress(ui, 51000);
  check(ui.screen == Screen::All, "then every sensor");
  // The button line itself (high = released): a press bouncing on release is one step
  Ui b;
  uiButton(b, false, 1000);                       // press
  check(b.screen == Screen::Splash, "a clean press wakes it");
  uiButton(b, true, 1200);                        // release...
  uiButton(b, false, 1201);                       // ...bouncing
  uiButton(b, true, 1202);
  check(b.screen == Screen::Splash, "release bounce is not a second press");
  uiButton(b, false, 2000);                       // next real press
  uiButton(b, true, 2005);                        // bouncing on the way down
  uiButton(b, false, 2010);
  check(b.screen == Screen::All, "press bounce is not a second press either");
  uiButton(b, true, 2300);
  uiButton(b, false, 2400);
  check(b.screen == Screen::Sensor && b.shown == 0, "the next clean press moves on");

  Ui splash;
  uiPress(splash, 100);
  uiTick(splash, 100 + AWAKE_MS + 1);
  check(splash.screen == Screen::Off, "the logo also goes off after 30 s");

  // Status LEDs: one GPIO each, next to its connector (hardware parts.py LED_PIN)
  const uint8_t ledPins[N_CONN] = {28, 27, 22, 9, 0, 1, 6, 7, 8};
  for (int c = 0; c < N_CONN; c++) check(CONN_LED[c] == ledPins[c], "LED pin of each connector");
  int reservedLeds = 0;
  for (uint8_t p : CONN_LED)
    for (uint8_t r : RESERVED) reservedLeds += p == r;
  check(reservedLeds == N_CONN, "every LED pin is reserved (never offered for a sensor)");
  // Patterns: on = measuring, blinking = not responding, off = not configured;
  // waiting for the Pi = a short flash every 2 s; the connector on the display blinks inverted
  check(ledOn(false, State::Ok, false, 100) && !ledOn(false, State::Ok, false, 500), "waiting: short flash");
  check(!ledOn(false, State::Ok, false, 2100 + 300), "waiting: flash every 2 s");
  check(ledOn(true, State::Ok, false, 500) && ledOn(true, State::Ok, false, 1500), "measuring: steady on");
  check(!ledOn(true, State::NotConfigured, false, 500) && !ledOn(true, State::NotConfigured, false, 1500),
        "no sensor there: off");
  check(ledOn(true, State::NotResponding, false, 500) != ledOn(true, State::NotResponding, false, 900),
        "not responding: blinking");
  check(!ledOn(true, State::Ok, true, 50) && ledOn(true, State::Ok, true, 500), "on the display: a dark blip");
  check(ledOn(true, State::NotConfigured, true, 50) && !ledOn(true, State::NotConfigured, true, 500),
        "on the display, nothing configured: a light blip");

  // The all-sensors screen: one bar per sensor, taller the nearer the obstacle
  check(barSegments(-1, 1200, 12) == 0, "nothing in range: flat");
  check(barSegments(1200, 1200, 12) == 0, "at the top of the scale: flat");
  check(barSegments(5000, 3000, 12) == 0, "beyond it: flat");
  check(barSegments(0, 1200, 12) == 12, "touching: full");
  check(barSegments(1199, 1200, 12) == 1, "just inside the scale: one segment");
  check(barSegments(600, 1200, 12) == 6, "halfway: half the segments");
  check(barSegments(1500, 3000, 12) == 6, "halfway on the sonar scale too");

  check(!checkConnectionText(500) && checkConnectionText(2500) && !checkConnectionText(4500),
         "not responding / check connection, 2 s each");

  if (failures) return 1;
  printf("all passed\n");
  return 0;
}
