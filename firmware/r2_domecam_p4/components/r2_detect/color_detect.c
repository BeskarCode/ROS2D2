// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "color_detect.h"

#include <math.h>
#include <stdlib.h>

bool color_model_valid(const color_model_t *m) {
  return m->h <= 179 && m->htol >= 2 && m->htol <= 40 && m->ltol >= 10 && m->ltol <= 120;
}

// RGB -> HSV with OpenCV's 8-bit scale (H 0-179, S and V 0-255).
static void to_hsv(int r, int g, int b, int *h, int *s, int *v) {
  int mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
  int mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
  int diff = mx - mn;
  *v = mx;
  *s = mx ? (diff * 255 + mx / 2) / mx : 0;
  if (!diff) {
    *h = 0;
    return;
  }
  float hf;
  if (mx == r) hf = 60.0f * (g - b) / diff;
  else if (mx == g) hf = 120.0f + 60.0f * (b - r) / diff;
  else hf = 240.0f + 60.0f * (r - g) / diff;
  if (hf < 0) hf += 360.0f;
  int hh = (int)lrintf(hf / 2.0f);
  *h = hh >= 180 ? hh - 180 : hh;
}

static int clampi(int x, int lo, int hi) { return x < lo ? lo : (x > hi ? hi : x); }

static bool matches(int r, int g, int b, const color_model_t *m) {
  int h, s, v;
  to_hsv(r, g, b, &h, &s, &v);
  if (s < clampi(m->s - m->ltol, 0, 255) || s > clampi(m->s + m->ltol, 0, 255)) return false;
  if (v < clampi(m->v - m->ltol, 0, 255) || v > clampi(m->v + m->ltol, 0, 255)) return false;
  int lo = m->h - m->htol, hi = m->h + m->htol;
  if (lo >= 0 && hi <= 179) return h >= lo && h <= hi;
  if (lo < 0) return h <= hi || h >= 180 + lo;   // red: hue wraps around 0/179
  return h >= lo || h <= hi - 180;
}

color_blob_t color_find(const uint8_t *rgb, int width, int height, const color_model_t *m,
                        const color_blob_t *prev, int step) {
  color_blob_t best = {false, 0, 0, 0};
  if (step < 1) step = 1;
  int gw = (width + step - 1) / step, gh = (height + step - 1) / step, n = gw * gh;
  uint8_t *mask = malloc((size_t)n);   // 1 = matches and not yet in a blob
  int *stack = malloc((size_t)n * sizeof(int));
  if (!mask || !stack) {
    free(mask);
    free(stack);
    return best;
  }
  for (int gy = 0; gy < gh; gy++)
    for (int gx = 0; gx < gw; gx++) {
      const uint8_t *p = rgb + ((size_t)gy * step * width + (size_t)gx * step) * 3;
      mask[gy * gw + gx] = matches(p[0], p[1], p[2], m);
    }

  bool use_prev = prev && prev->seen;
  float best_key = 0;
  for (int start = 0; start < n; start++) {   // raster order, like cv2.connectedComponents
    if (!mask[start]) continue;
    long count = 0;
    double sx = 0, sy = 0;
    int top = 0;
    stack[top++] = start;
    mask[start] = 0;
    while (top) {
      int i = stack[--top], x = i % gw, y = i / gw;
      count++;
      sx += x;
      sy += y;
      for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++) {
          int nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= gw || ny >= gh) continue;
          int j = ny * gw + nx;
          if (mask[j]) {
            mask[j] = 0;
            stack[top++] = j;
          }
        }
    }
    float area = (float)count / n;
    if (area < COLOR_MIN_AREA) continue;
    color_blob_t c = {true, (float)(sx / count * step / width), (float)(sy / count * step / height), area};
    float key = use_prev ? hypotf(c.cx - prev->cx, c.cy - prev->cy) : -area;
    if (!best.seen || key < best_key) {
      best = c;
      best_key = key;
    }
  }
  free(mask);
  free(stack);
  return best;
}
