// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The detector task (core 1): faces with Espressif's human_face_detect, or a colour with the same
// search as the Pi (color_detect.c). Never both. The results go out as lines on :82/faces.
#include "detect.h"

#include <stdio.h>
#include <string.h>

#include "camera.h"
#include "color_detect.h"
#include "config.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "faces_line.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "human_face_detect.hpp"
#include "web.h"

static const char *TAG = "detect";

#define MAX_FACES 8
#define LINE_SIZE 512

static volatile int s_mode = CAM_DETECT_FACES ? DETECT_FACES : DETECT_NONE;
static color_model_t s_color = {0, 0, 0, 10, 60};
static volatile int s_score1 = 50, s_score2 = 50;   // %, MSR and MNP thresholds
static volatile bool s_scores_changed;
static SemaphoreHandle_t s_lock;
static char s_line[LINE_SIZE];   // the newest line, guarded by s_lock
static uint32_t s_line_seq;
static volatile float s_fps;
static int s_clients;

// ---------------------------------------------------------------- the task

static void publish(const faces_line_t *l) {
  char buf[LINE_SIZE];
  if (faces_line_format(buf, sizeof(buf), l) < 0) return;
  xSemaphoreTake(s_lock, portMAX_DELAY);
  strcpy(s_line, buf);
  s_line_seq++;
  xSemaphoreGive(s_lock);
}

static void detect_task(void *arg) {
  HumanFaceDetect *faces = new HumanFaceDetect();
  frame_t f = {};
  color_blob_t prev = {false, 0, 0, 0};
  int last_mode = -1, frames = 0;
  int64_t fps_start = esp_timer_get_time(), last_warn = 0;
  for (;;) {
    int mode = s_mode;
    if (mode != last_mode) {   // a new search starts from scratch
      prev.seen = false;
      frames = 0;
      fps_start = esp_timer_get_time();
      last_mode = mode;
    }
    if (mode == DETECT_NONE || !camera_ok()) {
      s_fps = 0;
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }
    int width = mode == DETECT_FACES ? DETECT_FACE_WIDTH : DETECT_COLOR_WIDTH;
    if (!camera_get_frame(&f, FRAME_RGB888, width, pdMS_TO_TICKS(500))) continue;

    faces_line_t l = {};
    face_box_t boxes[MAX_FACES];
    l.seq = f.seq;
    l.w = f.width;
    l.h = f.height;
    l.rot = camera_rotate();
    l.mode = mode;
    if (mode == DETECT_FACES) {
      if (s_scores_changed) {
        s_scores_changed = false;
        faces->set_score_thr(s_score1 / 100.0f, 0);
        faces->set_score_thr(s_score2 / 100.0f, 1);
      }
      dl::image::img_t img = {.data = f.buf, .width = (uint16_t)f.width, .height = (uint16_t)f.height,
                              .pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB888};
      std::list<dl::detect::result_t> &res = faces->run(img);
      res.sort([](const dl::detect::result_t &a, const dl::detect::result_t &b) {   // biggest first
        return (a.box[2] - a.box[0]) * (a.box[3] - a.box[1]) > (b.box[2] - b.box[0]) * (b.box[3] - b.box[1]);
      });
      for (auto &r : res) {
        if (l.n_faces == MAX_FACES) break;
        r.limit_box(f.width, f.height);
        boxes[l.n_faces++] = {r.box[0], r.box[1], r.box[2] - r.box[0], r.box[3] - r.box[1], r.score};
      }
      l.faces = boxes;
    } else {
      color_model_t m = s_color;
      prev = color_find(f.buf, f.width, f.height, &m, &prev, 1);
      l.marker = prev;
    }
    l.lat_ms = (uint32_t)((esp_timer_get_time() - f.grabbed_us) / 1000);
    camera_release(&f);
    publish(&l);

    frames++;
    int64_t now = esp_timer_get_time();
    if (now - fps_start >= 2000000) {
      s_fps = frames * 1e6f / (now - fps_start);
      frames = 0;
      fps_start = now;
      if (mode == DETECT_FACES && s_fps < 10 && now - last_warn > 60000000) {
        last_warn = now;
        ESP_LOGW(TAG, "faces at %.1f fps (< 10) with DETECT_FACE_WIDTH %d: try a smaller width",
                 (double)s_fps, DETECT_FACE_WIDTH);
      }
    }
  }
}

// ---------------------------------------------------------------- :82/faces

static esp_err_t faces_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "application/x-ndjson");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  __atomic_add_fetch(&s_clients, 1, __ATOMIC_RELAXED);
  uint32_t sent = 0;
  int64_t last = esp_timer_get_time();
  char buf[LINE_SIZE + 1];
  esp_err_t err = ESP_OK;
  while (err == ESP_OK) {
    xSemaphoreTake(s_lock, portMAX_DELAY);
    bool fresh = s_line_seq != sent;
    if (fresh) {
      sent = s_line_seq;
      strcpy(buf, s_line);
    }
    xSemaphoreGive(s_lock);
    int64_t now = esp_timer_get_time();
    if (fresh) {
      strcat(buf, "\n");
      err = httpd_resp_send_chunk(req, buf, strlen(buf));
      last = now;
    } else if (now - last > 2000000) {   // keep-alive: an empty line, like the S3 camera
      err = httpd_resp_send_chunk(req, "\n", 1);
      last = now;
    } else {
      vTaskDelay(pdMS_TO_TICKS(5));
    }
  }
  __atomic_sub_fetch(&s_clients, 1, __ATOMIC_RELAXED);
  return err;
}

// ---------------------------------------------------------------- /control and /status

static int set_detect(int v) { return v >= 0 && v <= 2 ? (s_mode = v, 0) : -1; }

static int set_score(volatile int *s, int v) {
  if (v < 1 || v > 99) return -1;
  *s = v;
  s_scores_changed = true;
  return 0;
}
static int set_score1(int v) { return set_score(&s_score1, v); }
static int set_score2(int v) { return set_score(&s_score2, v); }

static int set_color_field(uint8_t color_model_t::*field, int v) {
  if (v < 0 || v > 255) return -1;
  color_model_t m = s_color;
  m.*field = (uint8_t)v;
  if (!color_model_valid(&m)) return -1;
  s_color = m;
  return 0;
}
static int set_color_h(int v) { return set_color_field(&color_model_t::h, v); }
static int set_color_s(int v) { return set_color_field(&color_model_t::s, v); }
static int set_color_v(int v) { return set_color_field(&color_model_t::v, v); }
static int set_color_htol(int v) { return set_color_field(&color_model_t::htol, v); }
static int set_color_ltol(int v) { return set_color_field(&color_model_t::ltol, v); }

static int add_status(char *out, size_t size) {
  color_model_t m = s_color;
  return snprintf(out, size,
                  ",\"detect\":%d,\"faces_fps\":%.1f,\"faces_clients\":%d,\"score1\":%d,\"score2\":%d,"
                  "\"color\":[%d,%d,%d,%d,%d]",
                  s_mode, (double)s_fps, s_clients, s_score1, s_score2, m.h, m.s, m.v, m.htol, m.ltol);
}

void detect_start(void) {
  s_lock = xSemaphoreCreateMutex();
  web_register_control("detect", set_detect);
  web_register_control("score1", set_score1);
  web_register_control("score2", set_score2);
  web_register_control("color_h", set_color_h);
  web_register_control("color_s", set_color_s);
  web_register_control("color_v", set_color_v);
  web_register_control("color_htol", set_color_htol);
  web_register_control("color_ltol", set_color_ltol);
  web_register_status(add_status);

  httpd_handle_t h = web_start_port(82, 32770);
  const httpd_uri_t uri = {.uri = "/faces", .method = HTTP_GET, .handler = faces_handler, .user_ctx = NULL};
  if (h) httpd_register_uri_handler(h, &uri);
  xTaskCreatePinnedToCore(detect_task, "detect", 16384, NULL, 5, NULL, 1);
}
