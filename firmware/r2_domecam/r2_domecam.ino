// r2_domecam: a camera for R2's dome, sent over WiFi to the Raspberry Pi. Runs on a
// Seeed XIAO ESP32S3 Sense or an AI-Thinker ESP32-CAM, both with an OV2640. The dome turns, so no cables: power from the dome's 5 V, picture
// by WiFi.
//
//   http://r2-domecam1.local:81/stream   MJPEG for the Pi (one viewer at a time)
//   http://r2-domecam1.local/            page with the picture and the status
//   http://r2-domecam1.local/status      JSON: fps, WiFi signal, temperature, uptime...
//   http://r2-domecam1.local/capture     one JPEG
//   http://r2-domecam1.local/control?var=framesize&val=5   framesize, quality, vflip, hmirror
//
// The Pi's camera node uses it as source: http://r2-domecam1.local:81/stream (or the IP).
//
// Arduino IDE, esp32 core 3.x:
//   XIAO ESP32S3 Sense: board "XIAO_ESP32S3", PSRAM "OPI PSRAM" (the camera needs it)
//   ESP32-CAM:          board "AI Thinker ESP32-CAM" (PSRAM is on by default)
// Copy config.example.h to config.h, pick the board and fill in the WiFi first.
//
// Built for low lag, which is what made the dome overshoot in the proof of concept:
// the camera always hands over its newest picture, WiFi power saving is off, and the
// stream has no extras.

#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "config.h"

#if defined(BOARD_XIAO_ESP32S3_SENSE)
// XIAO ESP32S3 Sense camera pins (Seeed's wiring of the B2B connector)
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13
#define LED_PIN        21      // the XIAO's orange LED, on when LOW

#elif defined(BOARD_ESP32_CAM)
// AI-Thinker ESP32-CAM camera pins
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM   0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM     5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22
#define LED_PIN        33      // the small red LED on the back, on when LOW
                               // (GPIO 4 is the big white flash: never used here)
#else
#error "Pick the board in config.h: BOARD_XIAO_ESP32S3_SENSE or BOARD_ESP32_CAM"
#endif

static httpd_handle_t web = nullptr;      // port 80: page, status, capture, control
static httpd_handle_t streamer = nullptr; // port 81: the stream on its own, so it never waits

static volatile bool streaming = false;
static volatile uint32_t framesSent = 0;
static volatile float fps = 0;
static uint32_t lastWifiCheck = 0;

// ---------------------------------------------------------------- camera

static bool startCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;  c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM;  c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM;  c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;  c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;          // the OV2640 compresses: the ESP32 only forwards
  c.frame_size = CAM_FRAMESIZE;
  c.jpeg_quality = CAM_QUALITY;
  c.fb_count = 2;                           // one being filled while the other is sent
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;         // never send an old picture: old = lag

  if (!psramFound()) {
    Serial.println("No PSRAM: XIAO -> Tools > PSRAM > OPI PSRAM; ESP32-CAM -> board AI Thinker ESP32-CAM");
    return false;
  }
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed 0x%x: is the camera ribbon latched (and the XIAO's Sense board clicked on)?\n", err);
    return false;
  }
  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, CAM_VFLIP);
  s->set_hmirror(s, CAM_HMIRROR);
  return true;
}

// ---------------------------------------------------------------- stream (port 81)

#define BOUNDARY "r2domecamframe"
static const char *STREAM_TYPE = "multipart/x-mixed-replace;boundary=" BOUNDARY;
static const char *PART = "\r\n--" BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t streamHandler(httpd_req_t *req) {
  // One viewer at a time: a second one would halve everybody's frame rate
  if (streaming) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_sendstr(req, "busy: another viewer has the stream\n");
    return ESP_OK;
  }
  streaming = true;
  digitalWrite(LED_PIN, LOW);
  httpd_resp_set_type(req, STREAM_TYPE);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");

  char head[96];
  esp_err_t res = ESP_OK;
  uint32_t count = 0, t0 = millis();
  while (res == ESP_OK) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) { res = ESP_FAIL; break; }
    size_t n = snprintf(head, sizeof(head), PART, (unsigned)fb->len);
    res = httpd_resp_send_chunk(req, head, n);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    framesSent++;
    if (++count == 30) {
      fps = 30000.0f / (millis() - t0);
      count = 0;
      t0 = millis();
    }
  }
  streaming = false;
  fps = 0;
  digitalWrite(LED_PIN, HIGH);
  return res;
}

// ---------------------------------------------------------------- page, status, capture, control (port 80)

static esp_err_t statusHandler(httpd_req_t *req) {
  sensor_t *s = esp_camera_sensor_get();
  char json[400];
  snprintf(json, sizeof(json),
           "{\"name\":\"%s\",\"ip\":\"%s\",\"rssi\":%d,\"fps\":%.1f,\"streaming\":%s,"
           "\"frames\":%lu,\"framesize\":%d,\"quality\":%d,\"vflip\":%d,\"hmirror\":%d,"
           "\"temp_c\":%.1f,\"uptime_s\":%lu,\"heap\":%lu,\"psram_free\":%lu}",
           CAM_HOSTNAME, WiFi.localIP().toString().c_str(), WiFi.RSSI(), fps, streaming ? "true" : "false",
           (unsigned long)framesSent, s->status.framesize, s->status.quality, s->status.vflip, s->status.hmirror,
           temperatureRead(), (unsigned long)(millis() / 1000), (unsigned long)ESP.getFreeHeap(),
           (unsigned long)ESP.getFreePsram());
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, json);
}

static esp_err_t captureHandler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return httpd_resp_send_500(req);
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// /control?var=framesize&val=5   (also quality, vflip, hmirror). Lasts until the next reboot.
static esp_err_t controlHandler(httpd_req_t *req) {
  char query[64], var[16], val[8];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK ||
      httpd_query_key_value(query, "var", var, sizeof(var)) != ESP_OK ||
      httpd_query_key_value(query, "val", val, sizeof(val)) != ESP_OK) {
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "use ?var=framesize|quality|vflip|hmirror&val=N");
  }
  sensor_t *s = esp_camera_sensor_get();
  int v = atoi(val), r = -1;
  if (!strcmp(var, "framesize")) r = s->set_framesize(s, (framesize_t)v);
  else if (!strcmp(var, "quality")) r = s->set_quality(s, v);
  else if (!strcmp(var, "vflip")) r = s->set_vflip(s, v);
  else if (!strcmp(var, "hmirror")) r = s->set_hmirror(s, v);
  if (r != 0) return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "unknown var or value");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, "ok\n");
}

static const char PAGE[] = R"HTML(<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>r2_domecam</title>
<style>body{margin:0;background:#0d1117;color:#e6edf3;font:14px system-ui,sans-serif;text-align:center}
img{max-width:100%;background:#000;margin-top:12px}pre{display:inline-block;text-align:left;color:#8b949e}</style>
</head><body><h3 id="h">r2_domecam</h3><img id="v" alt="(the stream is busy if the Pi is using it)"><br><pre id="s"></pre>
<script>
const host=location.hostname;document.getElementById('v').src='http://'+host+':81/stream';
async function st(){try{const j=await(await fetch('/status')).json();document.getElementById('h').textContent=j.name+' - '+j.ip;
document.getElementById('s').textContent=JSON.stringify(j,null,1);}catch(e){}}
st();setInterval(st,2000);</script></body></html>)HTML";

static esp_err_t pageHandler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_sendstr(req, PAGE);
}

static void startServers() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = 80;
  cfg.ctrl_port = 32768;
  if (httpd_start(&web, &cfg) == ESP_OK) {
    httpd_uri_t page = {"/", HTTP_GET, pageHandler, nullptr};
    httpd_uri_t status = {"/status", HTTP_GET, statusHandler, nullptr};
    httpd_uri_t capture = {"/capture", HTTP_GET, captureHandler, nullptr};
    httpd_uri_t control = {"/control", HTTP_GET, controlHandler, nullptr};
    httpd_register_uri_handler(web, &page);
    httpd_register_uri_handler(web, &status);
    httpd_register_uri_handler(web, &capture);
    httpd_register_uri_handler(web, &control);
  }
  httpd_config_t scfg = HTTPD_DEFAULT_CONFIG();
  scfg.server_port = 81;
  scfg.ctrl_port = 32769;
  scfg.max_open_sockets = 3;
  if (httpd_start(&streamer, &scfg) == ESP_OK) {
    httpd_uri_t stream = {"/stream", HTTP_GET, streamHandler, nullptr};
    httpd_register_uri_handler(streamer, &stream);
  }
}

// ---------------------------------------------------------------- WiFi

static void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(CAM_HOSTNAME);
  WiFi.setSleep(false);              // power saving adds tens of ms of lag per picture
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Connecting to %s", WIFI_SSID);
  for (int i = 0; i < 60 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print('.');
    digitalWrite(LED_PIN, i % 2);    // blinking: looking for the WiFi
  }
  digitalWrite(LED_PIN, HIGH);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nNo WiFi: check config.h and that the antenna is plugged in. Retrying.");
    return;
  }
  Serial.printf("\nConnected: http://%s/  stream http://%s:81/stream  (RSSI %d dBm)\n",
                WiFi.localIP().toString().c_str(), WiFi.localIP().toString().c_str(), WiFi.RSSI());
  if (MDNS.begin(CAM_HOSTNAME)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("Also http://%s.local/\n", CAM_HOSTNAME);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  delay(300);
  Serial.println("\nr2_domecam");
  if (!startCamera()) {
    // Without a camera there is nothing to do: blink fast forever so it is obvious
    while (true) { digitalWrite(LED_PIN, !digitalRead(LED_PIN)); delay(100); }
  }
  connectWifi();
  startServers();
}

void loop() {
  // The router went away (or rebooted): the ESP32 reconnects by itself, but if it gives up
  // start again, so the dome camera always comes back without anyone touching it
  if (millis() - lastWifiCheck > 10000) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi lost, reconnecting");
      WiFi.disconnect();
      connectWifi();
    }
  }
  delay(100);
}
