// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "camera.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <unistd.h>

#include "config.h"
#include "driver/jpeg_encode.h"
#include "driver/ppa.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_video_device.h"
#include "esp_video_init.h"
#include "esp_video_ioctl.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "linux/videodev2.h"
#include "web.h"

static const char *TAG = "camera";

#define NBUF 3
#define SCCB_SDA 7   // shared with the audio codec, see README.md
#define SCCB_SCL 8

static int s_fd = -1, s_isp_fd = -1;
static uint8_t *s_buf[NBUF];
static int s_w, s_h;              // the sensor's picture, 1280x960
static int s_held = -1;           // V4L2 buffer kept as "the newest picture"
static uint32_t s_seq;
static int64_t s_grabbed_us;
static SemaphoreHandle_t s_lock;
static SemaphoreHandle_t s_new;   // given on every new picture
static ppa_client_handle_t s_ppa;
static jpeg_encoder_handle_t s_jpeg;
static bool s_ok;

static volatile int s_rotate = CAM_ROTATE, s_vflip = CAM_VFLIP, s_hmirror = CAM_HMIRROR;
static volatile int s_stream_w = CAM_STREAM_WIDTH, s_quality = CAM_JPEG_QUALITY;

bool camera_ok(void) { return s_ok; }
int camera_rotate(void) { return s_rotate; }
int camera_stream_width(void) { return s_stream_w; }
const char *camera_sensor(void) { return s_ok ? "OV5647" : "none"; }

static void capture_task(void *arg) {
  struct timeval tv = {.tv_sec = 1, .tv_usec = 0};   // DQBUF waits forever by default
  ioctl(s_fd, VIDIOC_S_DQBUF_TIMEOUT, &tv);
  int64_t last_ok = esp_timer_get_time(), last_warn = 0;
  for (;;) {
    struct v4l2_buffer b = {.type = V4L2_BUF_TYPE_VIDEO_CAPTURE, .memory = V4L2_MEMORY_MMAP};
    if (ioctl(s_fd, VIDIOC_DQBUF, &b) != 0) {
      int64_t now = esp_timer_get_time();
      if (now - last_ok > 2000000 && now - last_warn > 10000000) {   // every 10 s while stalled
        last_warn = now;
        ESP_LOGW(TAG, "no picture from the camera for %lld s (ribbon? power?)", (now - last_ok) / 1000000);
      }
      vTaskDelay(pdMS_TO_TICKS(10));
      continue;
    }
    last_ok = esp_timer_get_time();
    xSemaphoreTake(s_lock, portMAX_DELAY);
    int old = s_held;
    s_held = b.index;
    s_seq++;
    s_grabbed_us = esp_timer_get_time();
    xSemaphoreGive(s_lock);
    if (old >= 0) {   // give the previous one back to the driver
      struct v4l2_buffer q = {.type = V4L2_BUF_TYPE_VIDEO_CAPTURE, .memory = V4L2_MEMORY_MMAP, .index = old};
      ioctl(s_fd, VIDIOC_QBUF, &q);
    }
    xSemaphoreGive(s_new);
  }
}

static bool valid_width(int w) { return w == 320 || w == 640 || w == 800 || w == 1280; }

static size_t align_up(size_t n) { return (n + 127) & ~(size_t)127; }   // cache lines, for the PPA

bool camera_get_frame(frame_t *out, int fmt, int out_w, TickType_t wait) {
  if (!s_ok || !valid_width(out_w)) return false;
  TickType_t start = xTaskGetTickCount();
  for (;;) {   // wait for a picture newer than the caller's last one
    xSemaphoreTake(s_lock, portMAX_DELAY);
    bool fresh = s_held >= 0 && s_seq != out->seq;
    xSemaphoreGive(s_lock);
    if (fresh) break;
    TickType_t spent = xTaskGetTickCount() - start;
    if (spent >= wait || xSemaphoreTake(s_new, wait - spent) != pdTRUE) return false;
  }
  int out_h = s_h * out_w / s_w;
  int rot = s_rotate;
  bool turned = rot == 90 || rot == 270;
  int bpp = fmt == FRAME_RGB888 ? 3 : 2;
  size_t raw_len = align_up((size_t)out_w * out_h * bpp);
  uint8_t *raw = heap_caps_aligned_calloc(128, 1, raw_len, MALLOC_CAP_SPIRAM);
  if (!raw) return false;

  ppa_srm_oper_config_t op = {
      .in = {.pic_w = s_w, .pic_h = s_h, .block_w = s_w, .block_h = s_h, .srm_cm = PPA_SRM_COLOR_MODE_RGB565},
      .out = {.buffer = raw, .buffer_size = raw_len, .pic_w = turned ? out_h : out_w,
              .pic_h = turned ? out_w : out_h,
              .srm_cm = bpp == 3 ? PPA_SRM_COLOR_MODE_RGB888 : PPA_SRM_COLOR_MODE_RGB565},
      // the PPA turns counter-clockwise; CAM_ROTATE and /control rotate are clockwise
      .rotation_angle = rot == 90    ? PPA_SRM_ROTATION_ANGLE_270
                        : rot == 180 ? PPA_SRM_ROTATION_ANGLE_180
                        : rot == 270 ? PPA_SRM_ROTATION_ANGLE_90
                                     : PPA_SRM_ROTATION_ANGLE_0,
      .scale_x = (float)out_w / s_w,
      .scale_y = (float)out_w / s_w,
      .mirror_x = s_hmirror,
      .mirror_y = s_vflip,
      .rgb_swap = bpp == 3 && CAM_RGB_SWAP,
      .mode = PPA_TRANS_MODE_BLOCKING,
  };
  xSemaphoreTake(s_lock, portMAX_DELAY);   // the capture task must not give this buffer back meanwhile
  op.in.buffer = s_buf[s_held];
  out->seq = s_seq;
  out->grabbed_us = s_grabbed_us;
  esp_err_t err = ppa_do_scale_rotate_mirror(s_ppa, &op);
  xSemaphoreGive(s_lock);
  if (err != ESP_OK) {
    heap_caps_free(raw);
    return false;
  }
  out->width = turned ? out_h : out_w;
  out->height = turned ? out_w : out_h;

  if (fmt != FRAME_JPEG) {
    out->buf = raw;
    out->len = (size_t)out_w * out_h * bpp;
    return true;
  }
  jpeg_encode_memory_alloc_cfg_t mem = {.buffer_direction = JPEG_ENC_ALLOC_OUTPUT_BUFFER};
  size_t cap = 0;
  uint8_t *jpg = jpeg_alloc_encoder_mem(raw_len / 2 + 4096, &mem, &cap);
  uint32_t jlen = 0;
  jpeg_encode_cfg_t jc = {.width = out->width, .height = out->height, .src_type = JPEG_ENCODE_IN_FORMAT_RGB565,
                          .sub_sample = JPEG_DOWN_SAMPLING_YUV420, .image_quality = s_quality};
  err = jpg ? jpeg_encoder_process(s_jpeg, &jc, raw, raw_len, jpg, cap, &jlen) : ESP_ERR_NO_MEM;
  heap_caps_free(raw);
  if (err != ESP_OK) {
    heap_caps_free(jpg);
    return false;
  }
  out->buf = jpg;
  out->len = jlen;
  return true;
}

void camera_release(frame_t *f) {
  heap_caps_free(f->buf);
  f->buf = NULL;
}

// ---------------------------------------------------------------- /control and /status

static int set_ctrl(int fd, uint32_t cls, uint32_t id, int val) {
  struct v4l2_ext_control c = {.id = id, .value = val};
  struct v4l2_ext_controls cs = {.ctrl_class = cls, .count = 1, .controls = &c};
  return fd >= 0 && ioctl(fd, VIDIOC_S_EXT_CTRLS, &cs) == 0 ? 0 : -1;
}

static int set_framesize(int v) { return valid_width(v) ? (s_stream_w = v, 0) : -1; }
static int set_quality(int v) { return v >= 1 && v <= 100 ? (s_quality = v, 0) : -1; }
static int set_vflip(int v) { return v == 0 || v == 1 ? (s_vflip = v, 0) : -1; }
static int set_hmirror(int v) { return v == 0 || v == 1 ? (s_hmirror = v, 0) : -1; }
static int set_rotate(int v) { return v == 0 || v == 90 || v == 180 || v == 270 ? (s_rotate = v, 0) : -1; }
static int set_brightness(int v) { return set_ctrl(s_isp_fd, V4L2_CID_USER_CLASS, V4L2_CID_BRIGHTNESS, v); }
static int set_ae_level(int v) { return set_ctrl(s_fd, V4L2_CID_USER_CLASS, V4L2_CID_CAMERA_AE_LEVEL, v); }

static int add_status(char *out, size_t size) {
  return snprintf(out, size,
                  ",\"sensor\":\"%s\",\"sensor_mode\":\"%dx%d\",\"framesize\":%d,\"quality\":%d,"
                  "\"vflip\":%d,\"hmirror\":%d,\"rotate\":%d,\"frames\":%lu",
                  camera_sensor(), s_w, s_h, s_stream_w, s_quality, s_vflip, s_hmirror, s_rotate,
                  (unsigned long)s_seq);
}

// ---------------------------------------------------------------- start

static esp_err_t open_camera(void) {
  static const esp_video_init_csi_config_t csi = {
      .sccb_config = {.init_sccb = true,
                      .i2c_config = {.port = 0, .scl_pin = SCCB_SCL, .sda_pin = SCCB_SDA},
                      .freq = 100000},
      .reset_pin = -1,   // the Waveshare board has no reset or power-down line to the camera
      .pwdn_pin = -1,
  };
  static const esp_video_init_config_t cfg = {.csi = &csi};
  esp_err_t err = esp_video_init(&cfg);
  if (err != ESP_OK) return err;

  s_fd = open(ESP_VIDEO_MIPI_CSI_DEVICE_NAME, O_RDONLY);
  if (s_fd < 0) return ESP_ERR_NOT_FOUND;
  s_isp_fd = open(ESP_VIDEO_ISP1_DEVICE_NAME, O_RDWR);   // only for brightness

  struct v4l2_format f = {.type = V4L2_BUF_TYPE_VIDEO_CAPTURE};
  if (ioctl(s_fd, VIDIOC_G_FMT, &f) != 0) return ESP_FAIL;
  s_w = f.fmt.pix.width;   // the sensor mode chosen in sdkconfig.defaults
  s_h = f.fmt.pix.height;
  f.fmt.pix.pixelformat = V4L2_PIX_FMT_RGB565;
  if (ioctl(s_fd, VIDIOC_S_FMT, &f) != 0) return ESP_FAIL;

  struct v4l2_requestbuffers req = {.count = NBUF, .type = V4L2_BUF_TYPE_VIDEO_CAPTURE, .memory = V4L2_MEMORY_MMAP};
  if (ioctl(s_fd, VIDIOC_REQBUFS, &req) != 0) return ESP_FAIL;
  for (int i = 0; i < NBUF; i++) {
    struct v4l2_buffer b = {.type = V4L2_BUF_TYPE_VIDEO_CAPTURE, .memory = V4L2_MEMORY_MMAP, .index = i};
    if (ioctl(s_fd, VIDIOC_QUERYBUF, &b) != 0) return ESP_FAIL;
    s_buf[i] = mmap(NULL, b.length, PROT_READ | PROT_WRITE, MAP_SHARED, s_fd, b.m.offset);
    if (!s_buf[i] || ioctl(s_fd, VIDIOC_QBUF, &b) != 0) return ESP_FAIL;
  }
  int type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
  return ioctl(s_fd, VIDIOC_STREAMON, &type) == 0 ? ESP_OK : ESP_FAIL;
}

esp_err_t camera_start(void) {
  web_register_control("framesize", set_framesize);
  web_register_control("quality", set_quality);
  web_register_control("vflip", set_vflip);
  web_register_control("hmirror", set_hmirror);
  web_register_control("rotate", set_rotate);
  web_register_control("brightness", set_brightness);
  web_register_control("ae_level", set_ae_level);
  web_register_control("xclk", NULL);   // ESP32-S3 camera settings the P4 does not have
  web_register_control("aec2", NULL);
  web_register_control("zoom", NULL);
  web_register_control("gainceiling", NULL);
  web_register_status(add_status);

  s_lock = xSemaphoreCreateMutex();
  s_new = xSemaphoreCreateBinary();
  esp_err_t err = open_camera();
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "No camera (%s). Check the ribbon (README.md). WiFi and the web page keep "
                  "working; /status says \"sensor\":\"none\".", esp_err_to_name(err));
    return err;
  }
  ppa_client_config_t pc = {.oper_type = PPA_OPERATION_SRM};
  jpeg_encode_engine_cfg_t jc = {.timeout_ms = 100};
  if (ppa_register_client(&pc, &s_ppa) != ESP_OK || jpeg_new_encoder_engine(&jc, &s_jpeg) != ESP_OK) {
    ESP_LOGE(TAG, "PPA or JPEG encoder did not start");
    return ESP_FAIL;
  }
  s_ok = true;
  xTaskCreatePinnedToCore(capture_task, "capture", 4096, NULL, 6, NULL, 0);
  ESP_LOGI(TAG, "OV5647 %dx%d", s_w, s_h);
  return ESP_OK;
}
