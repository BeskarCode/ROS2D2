// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Face detection on the ESP32-S3 with Espressif's esp-dl (MSR finds candidates, MNP checks
// them). The two stages are set up exactly like Espressif's human_face_detect component
// (MIT license, https://github.com/espressif/esp-dl/tree/master/models/human_face_detect),
// with the models built into the sketch (face_models.cpp) instead of a flash partition.
#include <Arduino.h>
#include "face_detect.h"
#include "sdkconfig.h"

#if CONFIG_IDF_TARGET_ESP32S3
#include <algorithm>
#include <list>
#include "esp_camera.h"
#include "dl_detect_base.hpp"
#include "dl_detect_mnp_postprocessor.hpp"
#include "dl_detect_msr_postprocessor.hpp"
#include "dl_image_jpeg.hpp"

extern const uint8_t face_msr_model[];
extern const uint8_t face_mnp_model[];

namespace {

const float SCORE_THR = 0.5f;
const float NMS_THR = 0.5f;

// First stage: candidate faces in the whole picture
class MSR : public dl::detect::DetectImpl {
public:
  MSR() {
    m_model = new dl::Model((const char *)face_msr_model, fbs::MODEL_LOCATION_IN_FLASH_RODATA);
    m_model->minimize();
    m_image_preprocessor = new dl::image::ImagePreprocessor(m_model, {0, 0, 0}, {1, 1, 1}, true);
    m_postprocessor = new dl::detect::MSRPostprocessor(
        m_model, m_image_preprocessor, SCORE_THR, NMS_THR, 10,
        {{8, 8, 9, 9, {{16, 16}, {32, 32}}}, {16, 16, 9, 9, {{64, 64}, {128, 128}}}});
  }
};

// Second stage: looks closer at each candidate and keeps the real faces
class MNP {
  dl::Model *model;
  dl::image::ImagePreprocessor *pre;
  dl::detect::MNPPostprocessor *post;

public:
  MNP() {
    model = new dl::Model((const char *)face_mnp_model, fbs::MODEL_LOCATION_IN_FLASH_RODATA);
    model->minimize();
    pre = new dl::image::ImagePreprocessor(model, {0, 0, 0}, {1, 1, 1}, true);
    post = new dl::detect::MNPPostprocessor(model, pre, SCORE_THR, NMS_THR, 10, {{1, 1, 0, 0, {{48, 48}}}});
  }

  void setScore(float thr) { post->set_score_thr(thr); }

  std::list<dl::detect::result_t> &run(const dl::image::img_t &img, std::list<dl::detect::result_t> &candidates) {
    post->clear_result();
    for (auto &c : candidates) {
      int cx = (c.box[0] + c.box[2]) >> 1, cy = (c.box[1] + c.box[3]) >> 1;
      int side = std::max(c.box[2] - c.box[0], c.box[3] - c.box[1]);
      c.box[0] = cx - (side >> 1);
      c.box[1] = cy - (side >> 1);
      c.box[2] = c.box[0] + side;
      c.box[3] = c.box[1] + side;
      c.limit_box(img.width, img.height);
      pre->preprocess(img, c.box);
      model->run();
      post->postprocess();
    }
    post->nms();
    return post->get_result(img.width, img.height);
  }
};

SemaphoreHandle_t lock;
FaceResult latest = {};
volatile float detFps = 0;
volatile int rotation = 0;
volatile bool detectOn = true;       // false: the task sleeps on a notification, using no CPU
TaskHandle_t detectHandle = nullptr;
volatile float msrScore = SCORE_THR, mnpScore = SCORE_THR;   // changed from /control

// A test picture waiting to be searched (detectJpeg), and its result
const uint8_t *volatile testJpeg = nullptr;
volatile size_t testLen = 0;
FaceResult testResult;
volatile bool testDone = false;

// Turns an RGB888 picture clockwise into a new one (freed by the caller)
dl::image::img_t turn(const dl::image::img_t &src, int deg) {
  const int w = src.width, h = src.height;
  dl::image::img_t dst = src;
  if (deg == 90 || deg == 270) { dst.width = h; dst.height = w; }
  dst.data = heap_caps_malloc(w * h * 3, MALLOC_CAP_SPIRAM);
  if (!dst.data) return dst;
  const uint8_t *s = (const uint8_t *)src.data;
  uint8_t *d = (uint8_t *)dst.data;
  for (int y = 0; y < h; y++) {
    for (int x = 0; x < w; x++) {
      int nx, ny;
      if (deg == 90) { nx = h - 1 - y; ny = x; }
      else if (deg == 180) { nx = w - 1 - x; ny = h - 1 - y; }
      else { nx = y; ny = w - 1 - x; }
      memcpy(d + (ny * dst.width + nx) * 3, s + (y * w + x) * 3, 3);
    }
  }
  return dst;
}

void detectTask(void *) {
  MSR msr;
  MNP mnp;
  uint32_t count = 0, t0 = millis();
  float msrNow = SCORE_THR, mnpNow = SCORE_THR;
  for (;;) {
    while (!detectOn) ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // paused: no pictures taken, no CPU
    if (msrNow != msrScore) { msrNow = msrScore; msr.set_score_thr(msrNow); }
    if (mnpNow != mnpScore) { mnpNow = mnpScore; mnp.setScore(mnpNow); }
    bool test = testJpeg != nullptr && !testDone;
    uint32_t grabbed = millis();
    dl::image::img_t img;
    if (test) {
      dl::image::jpeg_img_t jpeg = {.data = (void *)testJpeg, .data_len = testLen};
      img = dl::image::sw_decode_jpeg(jpeg, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    } else {
      camera_fb_t *fb = esp_camera_fb_get();
      if (!fb) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
      dl::image::jpeg_img_t jpeg = {.data = fb->buf, .data_len = fb->len};
      img = dl::image::sw_decode_jpeg(jpeg, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
      esp_camera_fb_return(fb);            // give the picture back before the slow part
    }
    if (!img.data) {
      if (test) { testResult = {}; testDone = true; }
      vTaskDelay(pdMS_TO_TICKS(20));
      continue;
    }
    int rot = test ? 0 : rotation;
    if (rot) {
      dl::image::img_t turned = turn(img, rot);
      heap_caps_free(img.data);
      img = turned;
      if (!img.data) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
    }

    std::list<dl::detect::result_t> &found = mnp.run(img, msr.run(img));

    FaceResult r = {};
    r.grabbedMs = grabbed;
    r.width = img.width;
    r.height = img.height;
    r.rotate = rot;
    r.detectMs = millis() - grabbed;
    for (const auto &f : found) {
      if (r.count == MAX_FACES) break;
      Face &o = r.faces[r.count++];
      o.x = f.box[0];
      o.y = f.box[1];
      o.w = f.box[2] - f.box[0];
      o.h = f.box[3] - f.box[1];
      o.score = f.score;
    }
    heap_caps_free(img.data);
    std::sort(r.faces, r.faces + r.count, [](const Face &a, const Face &b) { return a.w * a.h > b.w * b.h; });

    if (test) {
      testResult = r;
      testDone = true;
      continue;
    }
    xSemaphoreTake(lock, portMAX_DELAY);
    r.seq = latest.seq + 1;
    latest = r;
    xSemaphoreGive(lock);

    if (++count == 20) {
      detFps = 20000.0f / (millis() - t0);
      count = 0;
      t0 = millis();
    }
  }
}

}  // namespace

bool setFaceRotate(int deg) {
  if (deg != 0 && deg != 90 && deg != 180 && deg != 270) return false;
  rotation = deg;
  return true;
}

int faceRotate() { return rotation; }

bool setFaceDetect(bool on) {
  if (!detectHandle) return false;
  detectOn = on;
  if (on) xTaskNotifyGive(detectHandle);   // wakes the task if it was paused
  return true;
}

bool faceDetect() { return detectOn; }

bool setFaceScore(int stage, int percent) {
  if (percent < 1 || percent > 99 || (stage != 1 && stage != 2)) return false;
  (stage == 1 ? msrScore : mnpScore) = percent / 100.0f;
  return true;
}

int faceScore(int stage) { return (int)((stage == 1 ? msrScore : mnpScore) * 100 + 0.5f); }

bool startFaceDetection(int rotate) {
  setFaceRotate(rotate);
  lock = xSemaphoreCreateMutex();
  // Core 1, away from WiFi (core 0). Priority 1, like setup() and loop(): higher would starve them
  return xTaskCreatePinnedToCore(detectTask, "faces", 16384, nullptr, 1, &detectHandle, 1) == pdPASS;
}

bool waitFaces(FaceResult &out, uint32_t afterSeq, uint32_t timeoutMs) {
  uint32_t start = millis();
  do {
    xSemaphoreTake(lock, portMAX_DELAY);
    bool fresh = latest.seq != afterSeq;
    if (fresh) out = latest;
    xSemaphoreGive(lock);
    if (fresh) return true;
    vTaskDelay(pdMS_TO_TICKS(3));
  } while (millis() - start < timeoutMs);
  return false;
}

bool detectJpeg(const uint8_t *jpeg, size_t len, FaceResult &out, uint32_t timeoutMs) {
  testDone = false;
  testLen = len;
  testJpeg = jpeg;
  uint32_t start = millis();
  while (!testDone && millis() - start < timeoutMs) vTaskDelay(pdMS_TO_TICKS(5));
  bool ok = testDone;
  if (ok) out = testResult;
  testJpeg = nullptr;   // a late result is dropped: testDone stays until the next test
  return ok;
}

float faceFps() { return detFps; }

#else  // ESP32-CAM and other boards without esp-dl: no detection, the Pi searches the stream

bool startFaceDetection(int) { return false; }
bool setFaceRotate(int) { return false; }
bool setFaceScore(int, int) { return false; }
bool setFaceDetect(bool) { return false; }
bool faceDetect() { return false; }
int faceScore(int) { return 0; }
int faceRotate() { return 0; }
bool waitFaces(FaceResult &, uint32_t, uint32_t timeoutMs) { delay(timeoutMs); return false; }
bool detectJpeg(const uint8_t *, size_t, FaceResult &, uint32_t) { return false; }
float faceFps() { return 0; }

#endif
