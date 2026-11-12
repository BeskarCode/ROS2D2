// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "faces_line.h"

#include <stdio.h>

#define ADD(...)                                              \
  do {                                                        \
    int k = snprintf(out + n, size - n, __VA_ARGS__);         \
    if (k < 0 || (size_t)k >= size - n) return -1;            \
    n += (size_t)k;                                           \
  } while (0)

int faces_line_format(char *out, size_t size, const faces_line_t *l) {
  size_t n = 0;
  if (!size) return -1;
  ADD("{\"seq\":%lu,\"lat_ms\":%lu,\"w\":%d,\"h\":%d,\"rot\":%d,\"mode\":\"%s\",\"faces\":[",
      (unsigned long)l->seq, (unsigned long)l->lat_ms, l->w, l->h, l->rot,
      l->mode == DETECT_COLOR ? "color" : "faces");
  for (int i = 0; l->mode != DETECT_COLOR && i < l->n_faces; i++) {
    const face_box_t *f = &l->faces[i];
    ADD("%s[%d,%d,%d,%d,%.2f]", i ? "," : "", f->x, f->y, f->w, f->h, (double)f->score);
  }
  ADD("]");
  if (l->mode == DETECT_COLOR) {
    if (l->marker.seen)
      ADD(",\"marker\":[%.3f,%.3f,%.3f]", (double)l->marker.cx, (double)l->marker.cy, (double)l->marker.area);
    else
      ADD(",\"marker\":null");
  }
  ADD("}");
  return (int)n;
}
