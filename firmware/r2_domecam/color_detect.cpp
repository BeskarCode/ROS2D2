// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "color_detect.h"

#include <math.h>

#include <vector>

namespace {

const float MIN_AREA = 0.004f;   // as find_marker's min_area on the Pi

// OpenCV's 8-bit HSV: H 0-179, S and V 0-255
void toHsv(uint8_t r, uint8_t g, uint8_t b, int &h, int &s, int &v) {
  int mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
  int mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
  int d = mx - mn;
  v = mx;
  s = mx ? (d * 255 + mx / 2) / mx : 0;
  if (d == 0) {
    h = 0;
    return;
  }
  float hh;
  if (mx == r) hh = 60.0f * (g - b) / d;
  else if (mx == g) hh = 120.0f + 60.0f * (b - r) / d;
  else hh = 240.0f + 60.0f * (r - g) / d;
  if (hh < 0) hh += 360.0f;
  h = (int)lroundf(hh / 2.0f) % 180;
}

bool inRange(int x, int lo, int hi) { return x >= lo && x <= hi; }

// The same test as match_mask: hue within htol (wrapping round 0/179), s and v within ltol
bool matches(int h, int s, int v, const ColorModel &m) {
  int sLo = m.s - m.ltol < 0 ? 0 : m.s - m.ltol, sHi = m.s + m.ltol > 255 ? 255 : m.s + m.ltol;
  int vLo = m.v - m.ltol < 0 ? 0 : m.v - m.ltol, vHi = m.v + m.ltol > 255 ? 255 : m.v + m.ltol;
  if (!inRange(s, sLo, sHi) || !inRange(v, vLo, vHi)) return false;
  int hLo = m.h - m.htol, hHi = m.h + m.htol;
  if (hLo >= 0 && hHi <= 179) return inRange(h, hLo, hHi);
  if (hLo < 0) return inRange(h, 0, hHi) || inRange(h, 180 + hLo, 179);
  return inRange(h, hLo, 179) || inRange(h, 0, hHi - 180);
}

}  // namespace

ColorBlob findColor(const uint8_t *rgb, int width, int height, const ColorModel &m,
                    const ColorBlob *prev, int step) {
  ColorBlob best = {};
  if (!rgb || width <= 0 || height <= 0 || step < 1) return best;
  const int gw = (width + step - 1) / step, gh = (height + step - 1) / step;
  const int cells = gw * gh;
  std::vector<uint8_t> mask(cells);
  for (int gy = 0; gy < gh; gy++) {
    const uint8_t *row = rgb + (size_t)(gy * step) * width * 3;
    for (int gx = 0; gx < gw; gx++) {
      const uint8_t *p = row + (size_t)(gx * step) * 3;
      int h, s, v;
      toHsv(p[0], p[1], p[2], h, s, v);
      mask[gy * gw + gx] = matches(h, s, v, m);
    }
  }

  // Blobs, 8-connected: each one's size and centre; keep the best as find_marker does
  std::vector<int> stack;
  float bestKey = 0;
  for (int start = 0; start < cells; start++) {
    if (!mask[start]) continue;
    long count = 0;
    double sx = 0, sy = 0;
    mask[start] = 0;
    stack.push_back(start);
    while (!stack.empty()) {
      int c = stack.back();
      stack.pop_back();
      int cx = c % gw, cy = c / gw;
      count++;
      sx += cx * step;
      sy += cy * step;
      for (int dy = -1; dy <= 1; dy++) {
        int ny = cy + dy;
        if (ny < 0 || ny >= gh) continue;
        for (int dx = -1; dx <= 1; dx++) {
          int nx = cx + dx;
          if (nx < 0 || nx >= gw) continue;
          int n = ny * gw + nx;
          if (mask[n]) {
            mask[n] = 0;
            stack.push_back(n);
          }
        }
      }
    }
    float area = (float)count / cells;
    if (area < MIN_AREA) continue;
    float bx = (float)(sx / count) / width, by = (float)(sy / count) / height;
    float key = (prev && prev->seen) ? hypotf(bx - prev->cx, by - prev->cy) : -area;
    if (!best.seen || key < bestKey) {
      best = {true, bx, by, area};
      bestKey = key;
    }
  }
  return best;
}
