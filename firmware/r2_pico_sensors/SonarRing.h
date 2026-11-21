// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Which HC-SR04 pings next. They take turns (one at a time, so they do not hear each other), and
// each turn can wait up to 40 ms for its echo; a lost one (not wired, or not answering) would waste
// its 40 ms every round. So a lost one is skipped, and tried again once a second in case it was
// plugged back in. No Arduino here: tested on its own (test/test_sonar_ring.cpp).
#pragma once

#include <stdint.h>

constexpr uint32_t SONAR_RETRY_MS = 1000;

// turn: the ring place that pinged last (-1 = none yet); lost[k] and lastTryMs[k] by ring place.
// Returns the ring place to ping now, or -1 when every one is lost and none is due for a retry.
inline int nextTurn(int turn, int n, const bool* lost, const uint32_t* lastTryMs, uint32_t nowMs) {
  for (int k = 1; k <= n; k++) {
    int i = (turn + k) % n;
    if (i < 0) i += n;
    if (!lost[i] || nowMs - lastTryMs[i] >= SONAR_RETRY_MS) return i;
  }
  return -1;
}
