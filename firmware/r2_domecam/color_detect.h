// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// A colour found on the camera itself, for the follow-a-colour mode, so the Pi gets where the
// colour is instead of the video. Same search as r2_vision/color_marker.py (match_mask +
// find_marker) on the Pi. Plain C++, no ESP32 parts: test/test_color_detect.py runs it on a PC.
#pragma once
#include <stdint.h>

struct ColorModel {
  uint8_t h;      // hue, OpenCV scale 0-179
  uint8_t s, v;   // 0-255
  uint8_t htol;   // hue tolerance (2-40)
  uint8_t ltol;   // tolerance on both saturation and brightness (10-120)
};

struct ColorBlob {
  bool seen;
  float cx, cy;   // centre, fractions 0-1 of the picture
  float area;     // fraction of the picture
};

// The blob of the colour nearest to prev (or the biggest, without prev), of at least 0.4 % of the
// picture. rgb: width*height pixels, 3 bytes each, R,G,B. Looks at every `step` pixel in both
// directions (step 2 = a quarter of the pixels).
ColorBlob findColor(const uint8_t *rgb, int width, int height, const ColorModel &m,
                    const ColorBlob *prev, int step = 2);
