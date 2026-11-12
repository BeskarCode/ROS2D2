// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_domecam_p4 settings. Copy this file to config.h and fill it in:
// config.h stays on your computer (it is in .gitignore), so the WiFi password is never pushed.
#pragma once

// WiFi: the Pi's own access point inside the droid ("R2D2"), never the home WiFi.
#define WIFI_SSID     "R2D2"
#define WIFI_PASSWORD "your-password"

// Name on the network: http://r2-domecam1.local/ . Use r2-domecam2, 3... for more cameras.
// The same name as the ESP32-S3 camera, so one can replace the other without touching the Pi.
#define CAM_HOSTNAME  "r2-domecam1"
