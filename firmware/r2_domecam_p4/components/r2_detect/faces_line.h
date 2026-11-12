// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// One line of :82/faces, the same format as the ESP32-S3 camera plus the mode and the colour blob:
//   {"seq":12,"lat_ms":48,"w":640,"h":480,"rot":0,"mode":"faces","faces":[[x,y,w,h,score],...]}
//   {"seq":13,"lat_ms":30,"w":320,"h":240,"rot":0,"mode":"color","faces":[],"marker":[cx,cy,area]}
// marker is null when the colour is not seen. Plain C: tested on the PC against the Pi's parser.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "color_detect.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  int x, y, w, h;
  float score;
} face_box_t;

enum { DETECT_NONE = 0, DETECT_FACES = 1, DETECT_COLOR = 2 };

typedef struct {
  uint32_t seq;
  uint32_t lat_ms;    // how long ago the picture was taken
  int w, h, rot;      // the picture as searched, turned rot degrees clockwise
  int mode;           // DETECT_FACES or DETECT_COLOR
  const face_box_t *faces;
  int n_faces;
  color_blob_t marker;
} faces_line_t;

// Writes the line without '\n'. Returns its length, or -1 if it does not fit in size.
int faces_line_format(char *out, size_t size, const faces_line_t *l);

#ifdef __cplusplus
}
#endif
