// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Find a colour in a picture: the biggest blob of it (or the one nearest to the last one seen).
// Same algorithm as r2_vision/color_marker.py (match_mask + find_marker) on the Pi, so the camera
// and the Pi find the same blob. Plain C, nothing from ESP-IDF: it is tested on the PC.
#pragma once
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  uint8_t h;     // OpenCV hue, 0-179
  uint8_t s, v;  // 0-255
  uint8_t htol;  // hue tolerance, 2-40
  uint8_t ltol;  // tolerance on both s and v, 10-120
} color_model_t;

typedef struct {
  bool seen;
  float cx, cy;  // centre, fractions of the picture (0-1)
  float area;    // fraction of the picture
} color_blob_t;

#define COLOR_MIN_AREA 0.004f

// The ranges the console and modes.yaml use.
bool color_model_valid(const color_model_t *m);

// rgb888: width*height pixels, R,G,B. Looks at every `step`-th pixel in both directions
// (1 = all). prev may be NULL or not seen: then the biggest blob wins.
color_blob_t color_find(const uint8_t *rgb888, int width, int height, const color_model_t *m,
                        const color_blob_t *prev, int step);

#ifdef __cplusplus
}
#endif
