// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Runs color_detect.cpp on the PC for test_color_detect.py:
//   color_cli picture.rgb width height h s v htol ltol [prev_cx prev_cy prev_area]
// picture.rgb: width*height*3 bytes, R,G,B. Prints "seen cx cy area".
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "color_detect.h"

int main(int argc, char **argv) {
  if (argc != 9 && argc != 12) {
    std::fprintf(stderr, "usage: color_cli picture.rgb width height h s v htol ltol [cx cy area]\n");
    return 2;
  }
  const int w = std::atoi(argv[2]), h = std::atoi(argv[3]);
  std::vector<uint8_t> rgb((size_t)w * h * 3);
  FILE *f = std::fopen(argv[1], "rb");
  if (!f || std::fread(rgb.data(), 1, rgb.size(), f) != rgb.size()) {
    std::fprintf(stderr, "cannot read %s\n", argv[1]);
    return 1;
  }
  std::fclose(f);
  ColorModel m;
  m.h = (uint8_t)std::atoi(argv[4]);
  m.s = (uint8_t)std::atoi(argv[5]);
  m.v = (uint8_t)std::atoi(argv[6]);
  m.htol = (uint8_t)std::atoi(argv[7]);
  m.ltol = (uint8_t)std::atoi(argv[8]);
  ColorBlob prev = {};
  const ColorBlob *p = nullptr;
  if (argc == 12) {
    prev.seen = true;
    prev.cx = (float)std::atof(argv[9]);
    prev.cy = (float)std::atof(argv[10]);
    prev.area = (float)std::atof(argv[11]);
    p = &prev;
  }
  ColorBlob b = findColor(rgb.data(), w, h, m, p);
  std::printf("%d %.4f %.4f %.5f\n", b.seen ? 1 : 0, b.cx, b.cy, b.area);
  return 0;
}
