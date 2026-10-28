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

// A status LED at time now: waiting for the Pi (not configured yet) = a short flash every 2 s;
// then on = measuring, blinking = not responding, off = no sensor on that connector. The
// connector on the display shows a short blip of the opposite every second.
inline bool ledOn(bool configured, State s, bool onDisplay, uint32_t now) {
  bool on;
  if (!configured) on = now % 2000 < 300;
  else if (s == State::Ok) on = true;
  else if (s == State::NotResponding) on = (now / 400) % 2;
  else on = false;
  if (configured && onDisplay && now % 1000 < 120) on = !on;
  return on;
}

// Display: off; a press shows the logo; the next one the last connector seen; then each
// press the next connector. 30 s without a press: off again (display and LEDs).
enum class Screen { Off, Splash, Sensor };
constexpr uint32_t AWAKE_MS = 30000, DEBOUNCE_MS = 50;

struct Ui {
  Screen screen = Screen::Off;
  int shown = 0;
  uint32_t lastPress = 0;
  bool pressedOnce = false;
  bool level = true;          // the button line: high = released (pull-up)
  uint32_t lastEdge = 0;
};

inline void uiPress(Ui& ui, uint32_t now) {
  if (ui.pressedOnce && now - ui.lastPress < DEBOUNCE_MS) return;
  ui.pressedOnce = true;
  ui.lastPress = now;
  if (ui.screen == Screen::Off) ui.screen = Screen::Splash;
  else if (ui.screen == Screen::Splash) ui.screen = Screen::Sensor;
  else ui.shown = (ui.shown + 1) % N_CONN;
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

inline void uiTick(Ui& ui, uint32_t now) {
  if (ui.screen != Screen::Off && now - ui.lastPress > AWAKE_MS) ui.screen = Screen::Off;
}
