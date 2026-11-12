// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The OV5647 through the P4's MIPI-CSI and ISP. A capture task keeps the newest picture; whoever
// needs one asks for it already scaled, turned and mirrored by the PPA, in the format it needs.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { FRAME_RGB888 = 0, FRAME_RGB565 = 1, FRAME_JPEG = 2 };

typedef struct {
  uint8_t *buf;        // owned by the caller until camera_release()
  size_t len;          // bytes in buf (the JPEG size for FRAME_JPEG)
  int width, height;   // after turning
  uint32_t seq;        // picture number; pass the last one back to wait for a newer one
  int64_t grabbed_us;  // esp_timer time the picture arrived
} frame_t;

esp_err_t camera_start(void);
bool camera_ok(void);

// The newest picture, out_w pixels wide before turning (320, 640, 800 or 1280; the height keeps
// 4:3), turned by camera_rotate() and mirrored by vflip/hmirror. Waits up to `wait` for a picture
// newer than out->seq. FRAME_RGB888 bytes are R,G,B. false: no camera, timeout or no memory.
bool camera_get_frame(frame_t *out, int fmt, int out_w, TickType_t wait);
void camera_release(frame_t *f);

int camera_rotate(void);           // 0, 90, 180, 270 clockwise
int camera_stream_width(void);     // the console video's width (/control framesize)
const char *camera_sensor(void);   // "OV5647" or "none"

#ifdef __cplusplus
}
#endif
