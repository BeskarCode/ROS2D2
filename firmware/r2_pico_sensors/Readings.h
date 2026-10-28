// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// What each sensor last said, shared by Tof.h, Sonar.h and the sketch.
#pragma once

#include "Config.h"

struct Reading {
  bool answers = false;   // 'O' in HB; false = 'N'
  bool fresh = false;     // a reading not yet sent in an R line
  int16_t mm = -1;        // -1 = answers, nothing in range
};

extern SensorCfg cfg[MAX_SENSORS];
extern Reading reading[MAX_SENSORS];
extern int nSensors;

inline void report(int i, int16_t mm) {
  reading[i].answers = true;
  reading[i].mm = mm;
  reading[i].fresh = true;
}

inline void lost(int i) {
  reading[i].answers = false;
  reading[i].fresh = false;
}
