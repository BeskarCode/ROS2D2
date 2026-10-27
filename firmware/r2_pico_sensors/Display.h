// The carrier board's display (SSD1306 128x64 on I2C 0x3C), its button and the diagnostic
// LEDs. Runs on the RP2350's second core (setup1/loop1), so the measuring never waits for it:
// the screen is drawn in RAM and sent one 128-byte page at a time, holding the I2C bus (shared
// with the VL53L0X, see i2cLock) only for that page. Without a display, nothing changes.
#pragma once

#include <Adafruit_GFX.h>
#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <Wire.h>
#include <pico/mutex.h>
#include <string.h>

#include "Board.h"
#include "Logo.h"
#include "Readings.h"

extern bool configured;
extern mutex_t i2cLock;

namespace display {

constexpr uint8_t ADDRESS = 0x3C;
constexpr uint32_t FRAME_MS = 200, PROBE_MS = 3000, LED_MS = 50;
constexpr uint8_t BRIGHT = 25;          // of 255: the 9 LEDs stay under ~100 mA

GFXcanvas1 canvas(128, 64);
Adafruit_NeoPixel leds(N_CONN, LED_PIN, NEO_GRB + NEO_KHZ800);
Ui ui;
bool present = false, lit = false;
uint32_t lastProbe = 0, lastFrame = 0, lastLeds = 0;

enum class State { NotConfigured, NotResponding, Ok };

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
  mutex_enter_blocking(&i2cLock);
  Wire.beginTransmission(ADDRESS);
  Wire.write(0x00);
  Wire.write(c, n);
  bool ok = Wire.endTransmission() == 0;
  mutex_exit(&i2cLock);
  return ok;
}

bool probe() {
  static const uint8_t init[] = {0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00,
                                 0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6};
  return command(init, sizeof init);
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
    mutex_enter_blocking(&i2cLock);
    Wire.beginTransmission(ADDRESS);
    Wire.write(0x40);
    Wire.write(data + x, CHUNK);
    bool ok = Wire.endTransmission() == 0;
    mutex_exit(&i2cLock);
    if (!ok) return false;
  }
  memcpy(sent[page], data, 128);
  return true;
}

void drawSplash() {
  canvas.fillScreen(0);
  canvas.drawBitmap(0, 8, LOGO, LOGO_W, LOGO_H, 1);
  canvas.setTextSize(1);
  canvas.setCursor(10, 40);
  canvas.print("ROS2D2 sensors");
  canvas.setCursor(10, 54);
  canvas.print("press for sensors >");
}

void drawSensor() {
  canvas.fillScreen(0);
  canvas.setTextSize(1);
  canvas.setCursor(0, 0);
  if (!configured) {
    canvas.setCursor(4, 28);
    canvas.print("Waiting for the Pi");
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
    canvas.print(s == State::NotResponding ? "NOT\nRESPONDING" : "NOT\nCONFIGURED");
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
    uint32_t col = 0;
    if (!configured) {
      if (now % 2000 < 300) col = leds.Color(0, 0, BRIGHT);              // waiting for the Pi
    } else {
      State s = stateOf(c, &mm);
      if (s == State::Ok) col = leds.Color(0, BRIGHT, 0);
      else if (s == State::NotResponding && (now / 400) % 2) col = leds.Color(BRIGHT, 0, 0);
    }
    if (ui.screen == Screen::Sensor && c == ui.shown && now % 1000 < 120) col = leds.Color(BRIGHT, BRIGHT, BRIGHT);
    leds.setPixelColor(c, col);
  }
  leds.show();
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  ui.level = digitalRead(BUTTON_PIN);
  leds.begin();
  leds.clear();
  leds.show();
}

void loop() {
  uint32_t now = millis();
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
    if (!on) {
      leds.clear();
      leds.show();
    }
  }
  if (!on) return;
  if (present && now - lastFrame >= FRAME_MS) {
    lastFrame = now;
    if (ui.screen == Screen::Splash) drawSplash();
    else drawSensor();
    for (int page = 0; page < 8 && present; page++) {
      present = sendPage(page);
      uiButton(ui, digitalRead(BUTTON_PIN), millis());     // a short tap is not missed
    }
    sentValid = present;
  }
  if (now - lastLeds >= LED_MS) {
    lastLeds = now;
    drawLeds(now);
  }
}

}  // namespace display
