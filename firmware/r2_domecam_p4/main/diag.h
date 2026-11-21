// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// What /status tells about the board itself, for the console's telemetry and to tell a reboot
// from a WiFi drop: firmware version, why it last started and how many times, chip temperature
// and how busy each core is (sampled once a second).
#pragma once

void diag_start(void);   // after nvs_flash_init; registers its part of /status
