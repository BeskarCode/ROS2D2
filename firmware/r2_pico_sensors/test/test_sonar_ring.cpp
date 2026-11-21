// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Host test of which HC-SR04 pings next: a lost one is skipped, and tried again once a second.
//   g++ -std=c++17 -Wall -I. test/test_sonar_ring.cpp -o /tmp/s && /tmp/s
#include <cstdio>

#include "SonarRing.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  if (!ok) {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main() {
  bool lost[5] = {false, true, false, true, false};
  uint32_t lastTry[5] = {0, 0, 0, 0, 0};

  // the ones measuring take turns; the lost ones are skipped
  check(nextTurn(-1, 5, lost, lastTry, 500) == 0, "first: 0");
  check(nextTurn(0, 5, lost, lastTry, 500) == 2, "0 -> 2 (1 is lost)");
  check(nextTurn(2, 5, lost, lastTry, 500) == 4, "2 -> 4 (3 is lost)");
  check(nextTurn(4, 5, lost, lastTry, 500) == 0, "4 -> 0");

  // a lost one gets its turn again once a second (maybe it was plugged back in)
  check(nextTurn(0, 5, lost, lastTry, 1000) == 1, "1 retried after 1 s");
  lastTry[1] = 1000;
  check(nextTurn(0, 5, lost, lastTry, 1500) == 2, "1 not again before 1 s");
  check(nextTurn(0, 5, lost, lastTry, 2000) == 1, "1 again at 2 s");

  // all lost: only the retries, and nothing in between
  bool all[3] = {true, true, true};
  uint32_t tries[3] = {900, 900, 900};
  check(nextTurn(0, 3, all, tries, 1000) == -1, "all lost, none due: idle");
  check(nextTurn(0, 3, all, tries, 1900) == 1, "all lost: the next one due");

  // none lost: plain round robin, the same as before
  bool none[3] = {false, false, false};
  uint32_t zero[3] = {0, 0, 0};
  check(nextTurn(2, 3, none, zero, 0) == 0 && nextTurn(0, 3, none, zero, 0) == 1, "round robin");
  check(nextTurn(-1, 0, none, zero, 0) == -1, "no sonars");

  printf(failures ? "sonar ring: %d failure(s)\n" : "sonar ring: all passed\n", failures);
  return failures ? 1 : 0;
}
