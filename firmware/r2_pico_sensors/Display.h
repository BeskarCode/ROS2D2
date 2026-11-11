// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The carrier board's display (SSD1306 128x64 on I2C 0x3C), its button and the status
// LEDs (one GPIO each). Runs on the RP2350's second core (setup1/loop1), so the measuring never waits for it:
// the screen is drawn in RAM and sent one 128-byte page at a time, holding the I2C bus (shared
// with the VL53L0X, see i2cLock) only for that page. Without a display, nothing changes.
#pragma once

#include <Adafruit_GFX.h>
#include <Arduino.h>
#include <Wire.h>
#include <pico/mutex.h>
#include <string.h>

#include "Board.h"
#include "Logo.h"
#include "Readings.h"
#include "Settings.h"
#include "Tof.h"

extern bool configured;
extern mutex_t i2cLock;

namespace display {

constexpr uint8_t ADDRESS = 0x3C;
// REFRESH_MS: a byte garbled on the bus (a loose contact) can reach the display as a command and
// roll the picture up (the bottom rows on top); every REFRESH_MS its settings and the whole
// picture are sent again, so such a glitch lasts a few seconds at most.
constexpr uint32_t FRAME_MS = 200, PROBE_MS = 3000, LED_MS = 20, REFRESH_MS = 5000;

GFXcanvas1 canvas(128, 64);
Ui ui;
bool present = false, lit = false;
uint32_t lastProbe = 0, lastFrame = 0, lastLeds = 0, lastRefresh = 0;

// What the Pi asked for (UI, DISP, ID). Written by core 0 (the serial line), applied by core 1.
constexpr int8_t REQ_NONE = -3, REQ_OFF = -2, REQ_ALL = -1;
UiCfg uiCfg;
volatile bool uiCfgChanged = false;
volatile int8_t dispReq = REQ_NONE;        // REQ_OFF, REQ_ALL or a connector 0..8
volatile int8_t identifyConn = -1;
volatile uint32_t identifyUntil = 0;

void applyUi(const UiCfg& c) {
  uiCfg = c;
  uiCfgChanged = true;
}
void requestDisplay(bool on, int screen) { dispReq = on ? (int8_t)screen : REQ_OFF; }
void identify(int c) {
  identifyUntil = millis() + IDENTIFY_MS;
  identifyConn = c;
}

// The sensor on connector c: its state and its reading
State stateOf(int c, int16_t* mm) {
  for (int i = 0; i < nSensors; i++) {
    if (connectorOf(cfg[i]) != c) continue;
    *mm = reading[i].mm;
    return reading[i].answers ? State::Ok : State::NotResponding;
  }
  return State::NotConfigured;
}

bool command(const uint8_t* c, size_t n) {
  i2cTake();
  Wire.beginTransmission(ADDRESS);
  Wire.write(0x00);
  Wire.write(c, n);
  bool ok = Wire.endTransmission() == 0;
  i2cGive();
  return ok;
}

// Everything the display keeps (start line, offset, addressing, orientation...), but not on/off
bool settings() {
  const uint8_t s[] = {0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00,
                       0xA1, 0xC8, 0xDA, 0x12, 0x81, CONTRAST[uiCfg.brightness & 3], 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6};
  return command(s, sizeof s);
}

bool probe() {
  uint8_t off = 0xAE;
  return command(&off, 1) && settings();
}

void power(bool on) {
  uint8_t c = on ? 0xAF : 0xAE;
  present = command(&c, 1) && present;
}

// One page (8 rows) of the canvas, as the SSD1306 wants it: one byte per column, LSB on top.
// Sent only if it changed since last time, in CHUNK-byte writes (~3.5 ms at 100 kHz each): the
// Wire timeout (10 ms, for the whole transfer) is never reached and the VL53L0X never wait long.
constexpr int CHUNK = 32;
uint8_t sent[8][128];
bool sentValid = false;

bool sendPage(int page) {
  uint8_t data[128];
  for (int x = 0; x < 128; x++) {
    uint8_t v = 0;
    for (int k = 0; k < 8; k++)
      if (canvas.getPixel(x, page * 8 + k)) v |= 1 << k;
    data[x] = v;
  }
  if (sentValid && memcmp(data, sent[page], 128) == 0) return true;
  const uint8_t where[] = {0x21, 0, 127, 0x22, (uint8_t)page, (uint8_t)page};
  if (!command(where, sizeof where)) return false;
  for (int x = 0; x < 128; x += CHUNK) {     // horizontal addressing: the column carries on
    i2cTake();
    Wire.beginTransmission(ADDRESS);
    Wire.write(0x40);
    Wire.write(data + x, CHUNK);
    bool ok = Wire.endTransmission() == 0;
    i2cGive();
    if (!ok) return false;
  }
  memcpy(sent[page], data, 128);
  return true;
}

void drawSplash() {
  canvas.fillScreen(0);
  // two-colour modules light rows 0-15 yellow: the title goes there, the logo (20 rows) below
  canvas.setTextSize(1);
  canvas.setCursor(22, 4);
  canvas.print("ROS2D2 sensors");
  canvas.drawBitmap(0, 22, LOGO, LOGO_W, LOGO_H, 1);
  canvas.setCursor(10, 52);
  canvas.print("press for sensors >");
}

void drawWaiting() {
  canvas.setCursor(4, 28);
  canvas.print("Waiting for the Pi");
}

// Every sensor at once, like a graphic equaliser: one bar per connector, taller the nearer the
// obstacle (12 segments over the same scale as drawSensor's: 1.2 m VL53L0X, 3 m HC-SR04), its
// number at its foot and the kind along the bottom. A working sensor with nothing in range is a
// flat line; not responding, a blinking x; nothing on that connector, only its number. The
// nearest two segments reach the yellow band of two-colour modules.
constexpr int SEGS = 12;

void drawAll(uint32_t now) {
  canvas.fillScreen(0);
  canvas.setTextSize(1);
  if (!configured) {
    drawWaiting();
    return;
  }
  canvas.setCursor(8, 57);
  canvas.print("VL53L0X");
  canvas.setCursor(72, 57);
  canvas.print("HC-SR04");
  for (int y = 0; y < 64; y += 2) canvas.drawPixel(57, y, 1);     // dotted: VL | HC
  for (int c = 0; c < N_CONN; c++) {
    bool vl = c < 4;
    int x = vl ? 2 + c * 14 : 60 + (c - 4) * 14;
    int16_t mm = -1;
    State s = stateOf(c, &mm);
    canvas.setCursor(x + 2, 48);
    canvas.print(vl ? c + 1 : c - 3);
    if (s == State::Ok) {
      canvas.drawFastHLine(x, 46, 10, 1);
      int lit = barSegments(mm, vl ? 1200 : 3000, SEGS);
      for (int k = 0; k < lit; k++) canvas.fillRect(x, 43 - 3 * k, 10, 2, 1);
    } else if (s == State::NotResponding && (now / 400) % 2) {
      canvas.setCursor(x + 2, 30);
      canvas.print('x');
    }
  }
}

void drawSensor(uint32_t now) {
  canvas.fillScreen(0);
  canvas.setTextSize(1);
  canvas.setCursor(0, 0);
  if (!configured) {
    drawWaiting();
    return;
  }
  int c = ui.shown;
  bool vl = c < 4;
  int16_t mm = -1;
  State s = stateOf(c, &mm);
  canvas.printf("%s %s GP%d", CONN_NAME[c], vl ? "VL53L0X" : "HC-SR04", vl ? CONN_XSHUT[c] : CONN_TRIG[c - 4]);
  if (!vl) canvas.printf("/%d", CONN_TRIG[c - 4] + 1);
  canvas.setCursor(0, 18);
  if (s == State::Ok) {
    canvas.setTextSize(3);
    if (mm < 0) canvas.print(" ---");
    else canvas.printf("%.2fm", mm / 1000.0);
    int top = vl ? 1200 : 3000;
    canvas.drawRect(0, 44, 128, 7, 1);
    if (mm > 0) canvas.fillRect(0, 44, min(127, mm * 127 / top), 7, 1);
  } else {
    canvas.setTextSize(2);
    if (s == State::NotConfigured) canvas.print("NOT\nCONFIGURED");
    else canvas.print(checkConnectionText(now) ? "CHECK\nCONNECTION" : "NOT\nRESPONDING");
  }
  canvas.setTextSize(1);
  canvas.setCursor(0, 56);
  if (s == State::Ok) canvas.print(mm < 0 ? "OK  out of range" : "OK");
  canvas.setCursor(104, 56);
  canvas.printf("%d/%d", c + 1, N_CONN);
}

void drawLeds(uint32_t now) {
  for (int c = 0; c < N_CONN; c++) {
    int16_t mm;
    State s = configured ? stateOf(c, &mm) : State::NotConfigured;
    bool identifying = c == identifyConn && (int32_t)(identifyUntil - now) > 0;
    digitalWrite(CONN_LED[c], ledOn(configured, s, ui.screen == Screen::Sensor && c == ui.shown, now, uiCfg.leds,
                                    ui.screen != Screen::Off, identifying));
  }
}

void ledsOff() {
  for (uint8_t p : CONN_LED) digitalWrite(p, LOW);
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  ui.level = digitalRead(BUTTON_PIN);
  for (uint8_t p : CONN_LED) pinMode(p, OUTPUT);
  ledsOff();
}

// The Pi's requests: new settings (timeout, brightness at once), the display on or off
void applyRequests(uint32_t now) {
  if (uiCfgChanged) {
    uiCfgChanged = false;
    ui.awake_ms = uiCfg.awake_ms;
    if (present && lit) {
      uint8_t c[] = {0x81, CONTRAST[uiCfg.brightness & 3]};
      command(c, sizeof c);
    }
  }
  int8_t req = dispReq;
  if (req == REQ_NONE) return;
  dispReq = REQ_NONE;
  if (req == REQ_OFF) {
    ui.screen = Screen::Off;
    return;
  }
  ui.screen = req == REQ_ALL ? Screen::All : Screen::Sensor;
  if (req >= 0) ui.shown = req;
  ui.lastPress = now;            // the timeout counts from here, as after a press
  ui.pressedOnce = true;
}

void loop() {
  uint32_t now = millis();
  applyRequests(now);
  uiButton(ui, digitalRead(BUTTON_PIN), now);
  uiTick(ui, now);
  bool on = ui.screen != Screen::Off;
  if (!present && now - lastProbe >= PROBE_MS) {     // plugged in later: found within 3 s
    lastProbe = now;
    present = probe();
    lit = false;
    sentValid = false;          // a display plugged in again shows nothing yet
  }
  if (on != lit) {
    lit = on;
    if (present) power(on);
  }
  // the LEDs, with the display on or off (their mode decides; ID blinks one whatever it is)
  if (now - lastLeds >= LED_MS) {
    lastLeds = now;
    drawLeds(now);
  }
  if (!on) return;
  if (present && now - lastFrame >= FRAME_MS) {
    lastFrame = now;
    if (now - lastRefresh >= REFRESH_MS) {
      lastRefresh = now;
      uint8_t on = 0xAF;
      present = settings() && command(&on, 1);
      sentValid = false;     // every page again, not only the ones that changed
    }
    if (ui.screen == Screen::Splash) drawSplash();
    else if (ui.screen == Screen::All) drawAll(now);
    else drawSensor(now);
    for (int page = 0; page < 8 && present; page++) {
      present = sendPage(page);
      uiButton(ui, digitalRead(BUTTON_PIN), millis());     // a short tap is not missed
    }
    sentValid = present;
  }
}

}  // namespace display
