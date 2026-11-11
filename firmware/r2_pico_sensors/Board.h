// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The carrier board (hardware/r2_pico_carrier): which connector each sensor is plugged into,
// and the display's button logic. Plain C++ (no Arduino): test/test_board.cpp runs anywhere.
#pragma once

#include <stdint.h>

#include "Config.h"

constexpr int N_CONN = 9;
// In the order of the status LEDs (LED1 = VL1 ... LED9 = US5)
const char* const CONN_NAME[N_CONN] = {"VL1", "VL2", "VL3", "VL4", "US1", "US2", "US3", "US4", "US5"};
constexpr uint8_t CONN_XSHUT[4] = {2, 3, 4, 5};
constexpr uint8_t CONN_TRIG[5] = {10, 12, 14, 18, 20};   // ECHO is the next GPIO
// Each connector's status LED, on its own GPIO (the nearest free one: hardware parts.py LED_PIN)
constexpr uint8_t CONN_LED[N_CONN] = {28, 27, 22, 9, 0, 1, 6, 7, 8};
constexpr uint8_t BUTTON_PIN = 26;

// The connector a configured sensor sits on, or -1 if its pins are not one of the board's
inline int connectorOf(const SensorCfg& s) {
  if (s.type == 'V') {
    for (int i = 0; i < 4; i++)
      if (s.a == CONN_XSHUT[i]) return i;
  } else if (s.type == 'S') {
    for (int i = 0; i < 5; i++)
      if (s.a == CONN_TRIG[i] && s.b == CONN_TRIG[i] + 1) return 4 + i;
  }
  return -1;
}

enum class State { NotConfigured, NotResponding, Ok };

// How the status LEDs behave (the Pi's UI led=...): Auto = only while the display is on (as it
// always was), On = also with the display off, Off = never, Errors = only the sensors not
// responding, blinking.
enum class LedMode { Auto, On, Off, Errors };

// A status LED at time now: waiting for the Pi (not configured yet) = a short flash every 2 s;
// then on = measuring, blinking = not responding, off = no sensor on that connector. The
// connector on the display shows a short blip of the opposite every second. Identifying (ID)
// blinks it at 5 Hz whatever the mode.
inline bool ledOn(bool configured, State s, bool onDisplay, uint32_t now, LedMode mode, bool displayOn,
                  bool identifying) {
  if (identifying) return (now / 100) % 2;
  if (mode == LedMode::Off || (mode == LedMode::Auto && !displayOn)) return false;
  if (mode == LedMode::Errors) return configured && s == State::NotResponding && (now / 400) % 2;
  bool on;
  if (!configured) on = now % 2000 < 300;
  else if (s == State::Ok) on = true;
  else if (s == State::NotResponding) on = (now / 400) % 2;
  else on = false;
  if (configured && onDisplay && now % 1000 < 120) on = !on;
  return on;
}

// Display: off; a press shows the logo; the next one every sensor at once; then each press one
// connector, VL1 to US5, and after US5 every sensor again. Held for 3 s, or 30 s without a
// press (Ui::awake_ms, the Pi's UI t=...; 0 = never): off again (display and LEDs).
enum class Screen { Off, Splash, All, Sensor };
constexpr uint32_t AWAKE_MS = 30000, HOLD_MS = 3000, DEBOUNCE_MS = 50;

struct Ui {
  Screen screen = Screen::Off;
  int shown = 0;
  uint32_t lastPress = 0;
  bool pressedOnce = false;
  bool level = true;          // the button line: high = released (pull-up)
  uint32_t lastEdge = 0;
  uint32_t awake_ms = AWAKE_MS;     // off this long after the last press; 0 = never
};

inline void uiPress(Ui& ui, uint32_t now) {
  if (ui.pressedOnce && now - ui.lastPress < DEBOUNCE_MS) return;
  ui.pressedOnce = true;
  ui.lastPress = now;
  if (ui.screen == Screen::Off) {
    ui.screen = Screen::Splash;
  } else if (ui.screen == Screen::Splash) {
    ui.screen = Screen::All;
  } else if (ui.screen == Screen::All) {
    ui.screen = Screen::Sensor;
    ui.shown = 0;
  } else if (ui.shown == N_CONN - 1) {
    ui.screen = Screen::All;
  } else {
    ui.shown++;
  }
}

// The button line as read (high = released). A press counts only when the line falls after
// being steadily high for DEBOUNCE_MS, so bounces on pressing and on releasing are ignored.
inline void uiButton(Ui& ui, bool high, uint32_t now) {
  if (high == ui.level) return;
  bool steady = now - ui.lastEdge >= DEBOUNCE_MS;
  ui.level = high;
  ui.lastEdge = now;
  if (!high && steady) uiPress(ui, now);
}

// The line still low HOLD_MS after the press that counted: a hold
inline void uiTick(Ui& ui, uint32_t now) {
  if (ui.screen == Screen::Off) return;
  bool held = !ui.level && now - ui.lastPress >= HOLD_MS;
  if (held || (ui.awake_ms && now - ui.lastPress > ui.awake_ms)) ui.screen = Screen::Off;
}

// The all-sensors screen: how many of a bar's n segments light for a reading of mm on a scale of
// top mm. The nearer the obstacle, the taller; nothing in range (-1) or beyond the scale: none.
inline int barSegments(int16_t mm, int top, int n) {
  if (mm < 0 || mm >= top) return 0;
  return (n * (top - mm) + top - 1) / top;
}

// A sensor not responding: the display says so, and every other 2 s where to look
inline bool checkConnectionText(uint32_t now) { return (now / 2000) % 2; }
