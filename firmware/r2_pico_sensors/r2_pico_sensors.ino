// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_pico_sensors: R2's distance sensors (VL53L0X, HC-SR04) on a Raspberry Pi Pico 2,
// read for the Pi 4 over USB serial. The Pi sends the sensors and their pins (CFG); the Pico
// measures and answers with text lines. Protocol and wiring: README.md.
// Core 0 measures and talks to the Pi; core 1 runs the carrier board's display, button and
// LEDs (Display.h), which only read what core 0 measured.
#include <Arduino.h>
#include <pico/mutex.h>

#include "Config.h"
#include "Readings.h"
#include "Sonar.h"
#include "Tof.h"
#include "Display.h"
#include "Mirror.h"

#define FW_VERSION "0.3.0"
#ifndef FW_COMMIT
#define FW_COMMIT "unknown"     // build.sh passes the git commit of firmware/r2_pico_sensors
#endif

constexpr uint8_t LED = LED_BUILTIN;   // GP25 on the Pico 2
constexpr uint32_t HB_MS = 1000, R_MS = 50, FLICKER_MS = 100;
constexpr size_t LINE_MAX = 200;

SensorCfg cfg[MAX_SENSORS];
Reading reading[MAX_SENSORS];
int nSensors = 0;
bool configured = false;

// The I2C bus is shared by the VL53L0X (core 0) and the display (core 1). Initialised before
// either setup() runs.
mutex_t i2cLock;
static struct I2cLockInit {
  I2cLockInit() { mutex_init(&i2cLock); }
} i2cLockInit;

char line[LINE_MAX + 1];
size_t lineLen = 0;
bool tooLong = false;
uint32_t lastHb = 0, lastR = 0, flickerUntil = 0;
bool readSinceHb = false;        // an R line went out since the last heartbeat (the LED blinks once)
const char* lastDs = nullptr;    // the display's screen as last told to the Pi (DS line)
mirror::State mir;               // the board mirror for the web console (MIR, Mirror.h)
uint32_t fbSeen = 1;             // display::fbSeq of the last picture looked at (odd: none yet)
bool fbOnSeen = false;

// Leave the pins of the last CFG quiet: XSHUT low keeps a VL53L0X off (its board pulls it up)
void releasePins() {
  sonar::stop();
  for (int i = 0; i < nSensors; i++) {
    if (cfg[i].type == 'V') {
      digitalWrite(cfg[i].a, LOW);
    } else {
      pinMode(cfg[i].a, INPUT);
      pinMode(cfg[i].b, INPUT);
    }
    lost(i);
  }
}

void onCfg(const char* args) {
  SensorCfg next[MAX_SENSORS];
  int n = 0;
  const char* err = parseCfg(args, next, &n);
  releasePins();
  nSensors = 0;
  configured = false;
  if (err) {
    Serial.printf("CFG ERR %s\n", err);
    return;
  }
  for (int i = 0; i < n; i++) {
    cfg[i] = next[i];
    reading[i] = Reading();
  }
  nSensors = n;
  configured = true;
  tof::begin();
  sonar::begin();
  Serial.printf("CFG OK %d\n", n);
}

void onLine(const char* l) {
  if (strcmp(l, "HELLO") == 0) {
    Serial.println("PICO r2_pico_sensors " FW_VERSION " proto 3 commit " FW_COMMIT);
    lastDs = nullptr;            // say what the display shows again
  } else if (strcmp(l, "CFG") == 0 || strncmp(l, "CFG ", 4) == 0) {
    onCfg(l + 3);
  } else if (strcmp(l, "TM 1") == 0 || strcmp(l, "TM 0") == 0) {
    tele::start(micros());
    tele::on = l[3] == '1';
    Serial.println("TM OK");
  } else if (strcmp(l, "MIR 1") == 0 || strcmp(l, "MIR 0") == 0) {
    mirror::request(mir, l[4] == '1', millis());
    display::mirrorWanted = mir.on;
    fbSeen = 1;                  // send the picture again
    Serial.println("MIR OK");
  } else if (strncmp(l, "PRESS ", 6) == 0) {
    mirror::Press p = mirror::parsePress(l + 6);
    if (p == mirror::Press::None) {
      Serial.println("PRESS ERR bad press");
    } else {
      display::requestPress(p == mirror::Press::Long);
      Serial.println("PRESS OK");
    }
  } else if (strncmp(l, "UI ", 3) == 0) {
    UiCfg next = display::uiCfg;
    const char* err = parseUi(l + 2, next);
    if (err) {
      Serial.printf("UI ERR %s\n", err);
    } else {
      display::applyUi(next);
      Serial.println("UI OK");
    }
  } else if (strncmp(l, "DISP ", 5) == 0) {
    bool on;
    int screen = -1;
    const char* err = parseDisp(l + 4, on, screen);
    if (err) {
      Serial.printf("DISP ERR %s\n", err);
    } else {
      display::requestDisplay(on, screen);
      Serial.println("DISP OK");
    }
  } else if (strncmp(l, "ID ", 3) == 0) {
    int c = parseConnector(l + 3);
    if (c < 0) {
      Serial.println("ID ERR bad connector");
    } else {
      display::identify(c);
      Serial.println("ID OK");
    }
  } else if (strcmp(l, "DBG") == 0) {
#ifndef WOKWI
    tof::debug();
#endif
    Serial.println("DBG end");
  } else if (strcmp(l, "BOOT") == 0) {
    Serial.flush();
    delay(50);
    rp2040.rebootToBootloader();
  } else if (*l) {
    Serial.println("ERR unknown");
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line[lineLen] = 0;
      if (tooLong) Serial.println("ERR too long");
      else onLine(line);
      lineLen = 0;
      tooLong = false;
    } else if (lineLen < LINE_MAX) {
      line[lineLen++] = c;
    } else {
      tooLong = true;
    }
  }
}

// TM: the last second's telemetry (Telemetry.h), right after the heartbeat
void sendTelemetry(uint32_t now) {
  uint32_t now_us = micros();
  char out[40 + MAX_SENSORS * 6];
  formatTm(out, sizeof out, tele::w, now_us - tele::windowStart, (int)(analogReadTemp() * 10),
           now / 1000, configured ? nSensors : 0);
  tele::start(now_us);
  Serial.println(out);
}

void sendHeartbeat(uint32_t now) {
  Serial.printf("HB %lu ", (unsigned long)now);
  if (configured) {
    char states[MAX_SENSORS + 1];
    for (int i = 0; i < nSensors; i++) states[i] = reading[i].answers ? 'O' : 'N';
    states[nSensors] = 0;
    Serial.println(states);
  } else {
    Serial.println("-");          // no CFG yet (or a bad one): telemetry and DS still go out
  }
  if (tele::on) sendTelemetry(now);
  // DS: what the display shows, when it changed (the console shows it and its buttons follow)
  const char* ds = display::shownName;
  if (ds != lastDs) {
    lastDs = ds;
    Serial.printf("DS %s\n", ds);
  }
  // the LED's one blink a second, if readings went out since the last heartbeat
  if (readSinceHb) flickerUntil = now + FLICKER_MS;
  readSinceHb = false;
}

void sendReadings(uint32_t now) {
  char out[MAX_SENSORS * 9 + 4] = "R";
  size_t len = 1;
  for (int i = 0; i < nSensors; i++) {
    if (!reading[i].fresh || !reading[i].answers) continue;
    len += snprintf(out + len, sizeof out - len, " %d:%d", i, reading[i].mm);
    reading[i].fresh = false;
  }
  if (len == 1) return;
  Serial.println(out);
  readSinceHb = true;
}

// The board mirror (MIR): the LEDs, the display's picture and the button, while the Pi asks
void sendMirror(uint32_t now) {
  static char out[3 + 1368 + 1];
  static uint8_t pages[1024];
  if (!mirror::active(mir, now)) {
    if (display::mirrorWanted) display::mirrorWanted = false;     // nobody looks any more
    display::btnEvent = 0;
    return;
  }
  if (mirror::ledLine(mir, display::ledLevels, now, out, sizeof out)) Serial.println(out);
  int8_t b = display::btnEvent;
  if (b) {
    display::btnEvent = 0;
    Serial.println(b == 2 ? "BTN long" : "BTN short");
  }
  bool on = display::fbOn;
  uint32_t seq = display::fbSeq;
  if (on == fbOnSeen && (seq == fbSeen || (seq & 1))) return;
  if (on) {
    if (seq & 1) return;                       // core 1 is copying: next time
    if (mir.fbSent && now - mir.fbAt < mirror::FB_MIN_MS) return;   // at most 5 pictures a second
    memcpy(pages, display::fbPages, sizeof pages);
    __sync_synchronize();
    if (display::fbSeq != seq) return;         // changed while copying: next time
  }
  if (mirror::fbLine(mir, pages, on, now, out, sizeof out)) Serial.println(out);   // false: same picture
  fbSeen = seq;
  fbOnSeen = on;
}

// Short flash once a second: waiting for the Pi's CFG. On, off for a moment once a second: measuring.
void led(uint32_t now) {
  bool on = configured ? (int32_t)(now - flickerUntil) >= 0 : now % 1000 < 200;
  digitalWrite(LED, on);
}

// Wokwi (wokwi/README.md) emulates only one core and has no Pi: there the display runs on core 0
// and the sketch configures itself, as the Pi would.
#ifdef WOKWI
constexpr char WOKWI_CFG[] = " V:2 V:3 V:4 S:10:11 S:12:13 S:14:15 S:18:19 S:20:21";
#endif

void setup() {
  pinMode(LED, OUTPUT);
  Serial.begin(115200);
  tof::setup();
#ifdef WOKWI
  display::setup();
  onCfg(WOKWI_CFG);
#endif
}

void loop() {
  uint32_t t0 = micros();
  readSerial();
  if (configured) {
    tof::loop();
    sonar::loop();
  }
  uint32_t now = millis();
  if (now - lastHb >= HB_MS) {
    lastHb = now;
    sendHeartbeat(now);
  }
  if (configured && now - lastR >= R_MS) {
    lastR = now;
    sendReadings(now);
  }
  led(now);
  sendMirror(now);
#ifdef WOKWI
  display::loop();
#endif
  tele::busy(micros() - t0);
}

#ifndef WOKWI
// Core 1: the display, its button and the status LEDs
void setup1() { display::setup(); }

void loop1() {
  uint32_t t0 = micros();
  display::loop();
  tele::busy(micros() - t0);
}
#endif
