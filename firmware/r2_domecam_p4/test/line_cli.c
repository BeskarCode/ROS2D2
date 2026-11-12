// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Test helper: line_cli faces|color|color_none|small -> one :82/faces line (or -1)
#include <stdio.h>
#include <string.h>
#include "faces_line.h"

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  face_box_t faces[2] = {{10, 20, 30, 40, 0.91f}, {100, 120, 50, 60, 0.5f}};
  faces_line_t l = {.seq = 12, .lat_ms = 48, .w = 640, .h = 480, .rot = 90, .mode = 1, .faces = faces, .n_faces = 2};
  char out[512];
  size_t size = sizeof(out);
  if (!strcmp(argv[1], "color") || !strcmp(argv[1], "color_none")) {
    l.mode = 2;
    l.n_faces = 0;
    l.marker = (color_blob_t){!strcmp(argv[1], "color"), 0.25f, 0.5f, 0.012f};
  } else if (!strcmp(argv[1], "small")) {
    size = 20;
  }
  int n = faces_line_format(out, size, &l);
  if (n < 0) {
    printf("-1\n");
    return 0;
  }
  printf("%s\n", out);
  return 0;
}
