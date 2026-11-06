// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_domecam: a camera for R2's dome, sent over WiFi to the Raspberry Pi. Runs on a
// Seeed XIAO ESP32S3 Sense or an AI-Thinker ESP32-CAM, both with an OV2640. The dome turns, so no cables: power from the dome's 5 V, picture
// by WiFi.
//
//   http://r2-domecam1.local:81/stream   MJPEG for the Pi (one viewer at a time)
//   http://r2-domecam1.local/            page with the picture and the status
//   http://r2-domecam1.local/status      JSON: fps, WiFi signal, temperature, uptime...
//   http://r2-domecam1.local/capture     one JPEG
//   http://r2-domecam1.local/control?var=framesize&val=5   framesize, quality, vflip, hmirror, rotate
//   http://r2-domecam1.local:82/faces    ESP32-S3 boards: the faces found on the camera itself,
//                                        one JSON line per picture (see face_detect.h)
//
// The Pi's camera node uses it as source: http://r2-domecam1.local:81/stream (or the IP).
//
// Arduino IDE, esp32 core 3.x:
//   XIAO ESP32S3 Sense: board "XIAO_ESP32S3", PSRAM "OPI PSRAM" (the camera needs it)
//   ESP32-CAM:          board "AI Thinker ESP32-CAM" (PSRAM is on by default)
//   ESP32-S3 WROOM CAM: board "ESP32S3 Dev Module", PSRAM "OPI PSRAM", Flash 16MB (N16R8)
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
#include "lwip/sockets.h"
#include "config.h"
#ifndef CAM_XCLK_MHZ          // config.h made before these settings existed
#define CAM_XCLK_MHZ  20
#endif
#ifndef CAM_LOW_LIGHT
#define CAM_LOW_LIGHT false
#endif
#include "face_detect.h"

#ifndef CAM_DETECT_FACES
#define CAM_DETECT_FACES true
#endif
#ifndef CAM_ROTATE
#define CAM_ROTATE 0
#endif

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
#define LED_ON         LOW

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
#define LED_ON         LOW

#elif defined(BOARD_ESP32S3_CAM)
// ESP32-S3 WROOM CAM (N16R8 / N8R8, Freenove and clones): same wiring as Espressif's ESP32-S3-EYE
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  15
#define SIOD_GPIO_NUM   4
#define SIOC_GPIO_NUM   5
#define Y9_GPIO_NUM    16
#define Y8_GPIO_NUM    17
#define Y7_GPIO_NUM    18
#define Y6_GPIO_NUM    12
#define Y5_GPIO_NUM    10
#define Y4_GPIO_NUM     8
#define Y3_GPIO_NUM     9
#define Y2_GPIO_NUM    11
#define VSYNC_GPIO_NUM  6
#define HREF_GPIO_NUM   7
#define PCLK_GPIO_NUM  13
#define LED_PIN         2      // Freenove's blue LED, on when HIGH (clones may have none)
#define LED_ON         HIGH
#else
#error "Pick the board in config.h: BOARD_XIAO_ESP32S3_SENSE, BOARD_ESP32_CAM or BOARD_ESP32S3_CAM"
#endif
#define LED_OFF        (!LED_ON)

static httpd_handle_t web = nullptr;      // port 80: page, status, capture, control
static httpd_handle_t streamer = nullptr; // port 81: the stream on its own, so it never waits
static httpd_handle_t facer = nullptr;    // port 82: the faces found here, for the Pi
static bool detecting = false;
static volatile bool facesSending = false;

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
  c.xclk_freq_hz = CAM_XCLK_MHZ * 1000000;   // slower clock = fewer fps but longer exposure
  c.pixel_format = PIXFORMAT_JPEG;          // the OV2640 compresses: the ESP32 only forwards
  c.frame_size = CAM_FRAMESIZE;
  c.jpeg_quality = CAM_QUALITY;
  c.fb_count = 3;                           // one being filled, one sent, one searched for faces
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
  if (CAM_LOW_LIGHT) {                      // indoors: let the sensor expose and amplify more
    s->set_aec2(s, 1);
    s->set_ae_level(s, 2);
    s->set_gainceiling(s, GAINCEILING_64X);
  }
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
  digitalWrite(LED_PIN, LED_ON);
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
  digitalWrite(LED_PIN, LED_OFF);
  return res;
}

// ---------------------------------------------------------------- faces (port 82)

// One line per picture searched, as soon as it is ready:
//   {"seq":12,"lat_ms":48,"w":320,"h":240,"rot":0,"faces":[[x,y,w,h,score],...]}   biggest first
// lat_ms is how long ago the picture was taken, so the Pi knows how old the faces are.
// The boxes are in the picture as searched: turned `rot` degrees clockwise (CAM_ROTATE).
static int facesJson(const FaceResult &r, char *line, size_t size) {
  int n = snprintf(line, size, "{\"seq\":%lu,\"lat_ms\":%lu,\"w\":%u,\"h\":%u,\"rot\":%u,\"faces\":[",
                   (unsigned long)r.seq, (unsigned long)(millis() - r.grabbedMs), r.width, r.height, r.rotate);
  for (int i = 0; i < r.count; i++) {
    const Face &f = r.faces[i];
    n += snprintf(line + n, size - n, "%s[%d,%d,%d,%d,%.2f]", i ? "," : "", f.x, f.y, f.w, f.h, f.score);
  }
  n += snprintf(line + n, size - n, "]}\n");
  return n;
}

static esp_err_t facesHandler(httpd_req_t *req) {
  if (facesSending) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_sendstr(req, "busy: another viewer has the faces\n");
    return ESP_OK;
  }
  facesSending = true;
  int one = 1;    // send each small line right away instead of waiting to fill a packet
  setsockopt(httpd_req_to_sockfd(req), IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
  httpd_resp_set_type(req, "application/x-ndjson");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");

  FaceResult r;
  uint32_t seq = 0;
  char line[64 + MAX_FACES * 40];
  esp_err_t res = ESP_OK;
  while (res == ESP_OK) {
    if (!waitFaces(r, seq, 1000)) {
      res = httpd_resp_send_chunk(req, "\n", 1);   // keep-alive, and notice when the Pi left
      continue;
    }
    seq = r.seq;
    res = httpd_resp_send_chunk(req, line, facesJson(r, line, sizeof(line)));
  }
  facesSending = false;
  return res;
}

// POST /detect with a JPEG as the body: the faces in that picture, to test the detector with a
// known picture:  curl --data-binary @face.jpg http://r2-domecam1.local/detect
static esp_err_t detectHandler(httpd_req_t *req) {
  if (!detecting) return httpd_resp_send_err(req, HTTPD_404_NOT_FOUND, "no face detection on this board");
  size_t len = req->content_len;
  if (len == 0 || len > 200000) return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "send a JPEG up to 200 KB");
  uint8_t *buf = (uint8_t *)heap_caps_malloc(len, MALLOC_CAP_SPIRAM);
  if (!buf) return httpd_resp_send_500(req);
  size_t got = 0;
  while (got < len) {
    int n = httpd_req_recv(req, (char *)buf + got, len - got);
    if (n <= 0) { heap_caps_free(buf); return httpd_resp_send_500(req); }
    got += n;
  }
  FaceResult r;
  bool ok = detectJpeg(buf, len, r, 5000);
  heap_caps_free(buf);
  if (!ok) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "the detector did not answer");
  char line[64 + MAX_FACES * 40];
  facesJson(r, line, sizeof(line));
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, line);
}

// ---------------------------------------------------------------- page, status, capture, control (port 80)

static esp_err_t statusHandler(httpd_req_t *req) {
  sensor_t *s = esp_camera_sensor_get();
  char json[400];
  snprintf(json, sizeof(json),
           "{\"name\":\"%s\",\"ip\":\"%s\",\"rssi\":%d,\"fps\":%.1f,\"streaming\":%s,"
           "\"frames\":%lu,\"framesize\":%d,\"quality\":%d,\"vflip\":%d,\"hmirror\":%d,"
           "\"faces_fps\":%.1f,\"faces_sending\":%s,\"rotate\":%d,"
           "\"temp_c\":%.1f,\"uptime_s\":%lu,\"heap\":%lu,\"psram_free\":%lu}",
           CAM_HOSTNAME, WiFi.localIP().toString().c_str(), WiFi.RSSI(), fps, streaming ? "true" : "false",
           (unsigned long)framesSent, s->status.framesize, s->status.quality, s->status.vflip, s->status.hmirror,
           faceFps(), facesSending ? "true" : "false", faceRotate(), temperatureRead(), (unsigned long)(millis() / 1000), (unsigned long)ESP.getFreeHeap(),
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

// zoom 2: the sensor sends only the middle of its picture (half as wide and high) at the same
// size, so faces come out twice as big and the fisheye's bent edges are left out. On the
// OV2640 that is a window of 400x300 in the middle of its fast 800x600 mode.
static int setZoom(sensor_t *s, int z) {
  if (z == 1) return s->set_framesize(s, CAM_FRAMESIZE);
  if (z != 2 || s->id.PID != OV2640_PID) return -1;
  return s->set_res_raw(s, 1 /* SVGA mode */, 0, 0, 0, 200, 150, 400, 300, 320, 240, false, false);
}

// /control?var=framesize&val=5   (also quality, vflip, hmirror, light...). Lasts until the next reboot.
static esp_err_t controlHandler(httpd_req_t *req) {
  char query[64], var[16], val[8];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK ||
      httpd_query_key_value(query, "var", var, sizeof(var)) != ESP_OK ||
      httpd_query_key_value(query, "val", val, sizeof(val)) != ESP_OK) {
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "use ?var=framesize|quality|vflip|hmirror|zoom|xclk|brightness|ae_level|aec2|gainceiling|rotate|score1|score2&val=N");
  }
  sensor_t *s = esp_camera_sensor_get();
  int v = atoi(val), r = -1;
  if (!strcmp(var, "framesize")) r = s->set_framesize(s, (framesize_t)v);
  else if (!strcmp(var, "quality")) r = s->set_quality(s, v);
  else if (!strcmp(var, "vflip")) r = s->set_vflip(s, v);
  else if (!strcmp(var, "hmirror")) r = s->set_hmirror(s, v);
  else if (!strcmp(var, "zoom")) r = setZoom(s, v);                               // 1 or 2
  else if (!strcmp(var, "xclk")) r = s->set_xclk(s, LEDC_TIMER_0, v);            // MHz
  else if (!strcmp(var, "brightness")) r = s->set_brightness(s, v);               // -2..2
  else if (!strcmp(var, "ae_level")) r = s->set_ae_level(s, v);                   // -2..2
  else if (!strcmp(var, "aec2")) r = s->set_aec2(s, v);                           // 0/1
  else if (!strcmp(var, "gainceiling")) r = s->set_gainceiling(s, (gainceiling_t)v);  // 0=2x..6=128x
  else if (!strcmp(var, "rotate")) r = setFaceRotate(v) ? 0 : -1;
  else if (!strcmp(var, "score1")) r = setFaceScore(1, v) ? 0 : -1;
  else if (!strcmp(var, "score2")) r = setFaceScore(2, v) ? 0 : -1;
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
  cfg.core_id = 0;                  // all web servers on core 0 with WiFi: core 1 is the face finder's
  if (httpd_start(&web, &cfg) == ESP_OK) {
    httpd_uri_t page = {"/", HTTP_GET, pageHandler, nullptr};
    httpd_uri_t status = {"/status", HTTP_GET, statusHandler, nullptr};
    httpd_uri_t capture = {"/capture", HTTP_GET, captureHandler, nullptr};
    httpd_uri_t control = {"/control", HTTP_GET, controlHandler, nullptr};
    httpd_register_uri_handler(web, &page);
    httpd_register_uri_handler(web, &status);
    httpd_register_uri_handler(web, &capture);
    httpd_register_uri_handler(web, &control);
    httpd_uri_t detect = {"/detect", HTTP_POST, detectHandler, nullptr};
    httpd_register_uri_handler(web, &detect);
  }
  httpd_config_t scfg = HTTPD_DEFAULT_CONFIG();
  scfg.server_port = 81;
  scfg.ctrl_port = 32769;
  scfg.max_open_sockets = 3;
  scfg.core_id = 0;
  if (httpd_start(&streamer, &scfg) == ESP_OK) {
    httpd_uri_t stream = {"/stream", HTTP_GET, streamHandler, nullptr};
    httpd_register_uri_handler(streamer, &stream);
  }
  if (detecting) {
    httpd_config_t fcfg = HTTPD_DEFAULT_CONFIG();
    fcfg.server_port = 82;
    fcfg.ctrl_port = 32770;
    fcfg.max_open_sockets = 3;
    fcfg.core_id = 0;
    if (httpd_start(&facer, &fcfg) == ESP_OK) {
      httpd_uri_t faces = {"/faces", HTTP_GET, facesHandler, nullptr};
      httpd_register_uri_handler(facer, &faces);
    }
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
  digitalWrite(LED_PIN, LED_OFF);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nNo WiFi: check config.h and that the antenna is plugged in. Retrying.");
    return;
  }
  Serial.printf("\nConnected: http://%s/  stream http://%s:81/stream  (RSSI %d dBm)\n",
                WiFi.localIP().toString().c_str(), WiFi.localIP().toString().c_str(), WiFi.RSSI());
  if (detecting) Serial.printf("Faces: http://%s:82/faces\n", WiFi.localIP().toString().c_str());
  if (MDNS.begin(CAM_HOSTNAME)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("Also http://%s.local/\n", CAM_HOSTNAME);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_OFF);
  delay(300);
  Serial.println("\nr2_domecam");
  if (!startCamera()) {
    // Without a camera there is nothing to do: blink fast forever so it is obvious
    while (true) { digitalWrite(LED_PIN, !digitalRead(LED_PIN)); delay(100); }
  }
  if (CAM_DETECT_FACES) {
    detecting = startFaceDetection(CAM_ROTATE);
    Serial.println(detecting ? "Face detection on the camera: on" : "Face detection on the camera: not on this board");
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
