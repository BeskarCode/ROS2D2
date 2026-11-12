// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Test helper: color_cli <file.rgb> W H h s v htol ltol step [prev_cx prev_cy prev_area]
//   -> "seen cx cy area";  color_cli --valid h s v htol ltol -> "1" or "0"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "color_detect.h"

int main(int argc, char **argv) {
  if (argc == 7 && !strcmp(argv[1], "--valid")) {
    int h = atoi(argv[2]);
    color_model_t m = {(uint8_t)(h > 255 ? 255 : h), (uint8_t)atoi(argv[3]), (uint8_t)atoi(argv[4]),
                       (uint8_t)atoi(argv[5]), (uint8_t)atoi(argv[6])};
    printf("%d\n", color_model_valid(&m) ? 1 : 0);
    return 0;
  }
  if (argc != 10 && argc != 13) return 2;
  int w = atoi(argv[2]), h = atoi(argv[3]);
  uint8_t *rgb = malloc((size_t)w * h * 3);
  FILE *f = fopen(argv[1], "rb");
  if (!f || !rgb || fread(rgb, 3, (size_t)w * h, f) != (size_t)w * h) return 3;
  fclose(f);
  color_model_t m = {(uint8_t)atoi(argv[4]), (uint8_t)atoi(argv[5]), (uint8_t)atoi(argv[6]),
                     (uint8_t)atoi(argv[7]), (uint8_t)atoi(argv[8])};
  color_blob_t prev = {false, 0, 0, 0};
  if (argc == 13) prev = (color_blob_t){true, (float)atof(argv[10]), (float)atof(argv[11]), (float)atof(argv[12])};
  color_blob_t b = color_find(rgb, w, h, &m, argc == 13 ? &prev : NULL, atoi(argv[9]));
  printf("%d %.5f %.5f %.5f\n", b.seen ? 1 : 0, b.cx, b.cy, b.area);
  free(rgb);
  return 0;
}
