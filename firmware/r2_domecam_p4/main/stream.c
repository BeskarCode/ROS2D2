// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "stream.h"

#include <stdio.h>

#include "camera.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "web.h"

#define BOUNDARY "r2domecamframe"

static volatile int s_clients;

int stream_clients(void) { return s_clients; }

static esp_err_t capture_handler(httpd_req_t *req) {
  frame_t f = {0};
  if (!camera_get_frame(&f, FRAME_JPEG, camera_stream_width(), pdMS_TO_TICKS(1000)))
    return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "no picture (is the camera connected?)");
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  esp_err_t err = httpd_resp_send(req, (const char *)f.buf, f.len);
  camera_release(&f);
  return err;
}

// MJPEG: only encodes while someone is watching (the console). Normal use sends no video.
static esp_err_t stream_handler(httpd_req_t *req) {
  if (!camera_ok()) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "no camera");
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=" BOUNDARY);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  s_clients++;
  frame_t f = {0};
  esp_err_t err = ESP_OK;
  char head[128];
  while (err == ESP_OK) {
    if (!camera_get_frame(&f, FRAME_JPEG, camera_stream_width(), pdMS_TO_TICKS(1000))) continue;
    int n = snprintf(head, sizeof(head), "\r\n--" BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                     (unsigned)f.len);
    err = httpd_resp_send_chunk(req, head, n);
    if (err == ESP_OK) err = httpd_resp_send_chunk(req, (const char *)f.buf, f.len);
    camera_release(&f);
  }
  s_clients--;
  return err;
}

static int add_status(char *out, size_t size) {
  return snprintf(out, size, ",\"stream_clients\":%d", s_clients);
}

void stream_start(httpd_handle_t web) {
  web_register_status(add_status);
  const httpd_uri_t cap = {.uri = "/capture", .method = HTTP_GET, .handler = capture_handler};
  if (web) httpd_register_uri_handler(web, &cap);
  httpd_handle_t s = web_start_port(81, 32769);
  const httpd_uri_t st = {.uri = "/stream", .method = HTTP_GET, .handler = stream_handler};
  if (s) httpd_register_uri_handler(s, &st);
}
