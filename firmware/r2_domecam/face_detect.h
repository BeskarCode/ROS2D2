// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Faces found on the camera itself (ESP32-S3 boards only), so the Pi gets a few numbers
// instead of having to receive and search every picture: less lag, and the Pi stays free.
// Uses Espressif's esp-dl face detector (MSR + MNP), which comes with the esp32 Arduino core.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "color_detect.h"

#define MAX_FACES 5

struct Face {
  int16_t x, y, w, h;      // box in pixels of the picture searched
  float score;             // 0-1
};

struct FaceResult {
  uint32_t seq;            // goes up by one with every picture searched
  uint32_t grabbedMs;      // millis() when the picture was taken
  uint16_t width, height;  // size of the picture searched (after turning it)
  uint16_t rotate;         // how much it was turned, degrees clockwise
  uint16_t detectMs;       // how long decoding + searching took
  uint8_t count;
  Face faces[MAX_FACES];   // biggest first, in the turned picture
  uint8_t mode;            // what was searched: 1 faces, 2 colour
  ColorBlob marker;        // the colour found (mode 2), in the turned picture
};

// Starts the detector in its own task. False on boards that cannot run it (ESP32-CAM).
// rotate: 0, 90, 180 or 270 degrees clockwise. The detector only finds upright faces, so
// a camera mounted on its side must have its picture turned before searching it.
bool startFaceDetection(int rotate);
bool setFaceRotate(int rotate);   // false if not 0/90/180/270
int faceRotate();
// What the camera searches: 0 nothing, 1 faces, 2 the colour set with setColorModel. Never
// faces and colour at once. False if out of range or on boards without detection.
bool setDetectMode(int mode);
int detectMode();
// The colour searched in mode 2 (same values and ranges as modes.yaml on the Pi).
void setColorModel(const ColorModel &m);
ColorModel colorModel();
// Pauses (false) or resumes (true) the face search (setDetectMode 0 or 1). Paused, the task sleeps without using CPU and
// takes no pictures, so the video gets the whole camera; waitFaces() then just times out.
// False on boards without detection.
bool setFaceDetect(bool on);
bool faceDetect();
// Lowest score kept, in percent: stage 1 = MSR (candidates), stage 2 = MNP (final check).
// Lower finds more (and harder) faces, but also more false ones. Default 50.
bool setFaceScore(int stage, int percent);
int faceScore(int stage);

// Waits up to timeoutMs for a result newer than afterSeq and copies it. False on timeout.
bool waitFaces(FaceResult &out, uint32_t afterSeq, uint32_t timeoutMs);

// Searches a JPEG sent from outside (POST /detect) instead of the next camera picture, as
// it is (not turned). For testing the detector with a known picture. False on timeout.
bool detectJpeg(const uint8_t *jpeg, size_t len, FaceResult &out, uint32_t timeoutMs);

// Pictures searched per second (0 when the detector is not running).
float faceFps();
