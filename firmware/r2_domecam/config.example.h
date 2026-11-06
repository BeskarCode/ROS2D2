// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_domecam settings. Copy this file to config.h and fill it in:
// config.h stays on your computer (it is in .gitignore), so the WiFi password is never pushed.
#pragma once

// Board: uncomment the one you have
#define BOARD_XIAO_ESP32S3_SENSE      // Seeed XIAO ESP32S3 Sense + OV2640
// #define BOARD_ESP32_CAM            // AI-Thinker ESP32-CAM (the common one) + OV2640
// #define BOARD_ESP32S3_CAM          // ESP32-S3 WROOM CAM, N16R8 or N8R8 (Freenove and clones)

// WiFi (hidden networks work too)
#define WIFI_SSID     "your-network"
#define WIFI_PASSWORD "your-password"

// Name on the network: http://r2-domecam1.local/ . Use r2-domecam2, 3... for more cameras.
#define CAM_HOSTNAME  "r2-domecam1"

// Picture sent to the Pi. The face detector works at 320 px wide, so QVGA is enough and
// fastest; VGA gives a sharper picture for the web console at fewer frames per second.
//   FRAMESIZE_QVGA  320x240     FRAMESIZE_VGA  640x480     FRAMESIZE_SVGA 800x600
#define CAM_FRAMESIZE FRAMESIZE_QVGA
#define CAM_QUALITY   12      // JPEG quality 4 (best, bigger) .. 63 (worst, smaller)

// Light. A slower clock gives each picture more time to collect light (20 MHz ~ 40 fps in QVGA,
// 10 MHz ~ 20 fps: still more than the Pi needs). CAM_LOW_LIGHT raises exposure and gain.
// (Also from /control?var=xclk|ae_level|aec2|gainceiling|brightness&val=N until the next reboot.)
#define CAM_XCLK_MHZ  10
#define CAM_LOW_LIGHT true

// Mounting: the OV2640 on the Sense board sees the world upside down or mirrored
// depending on how it sits in the dome. Fix it here (or later from /control).
#define CAM_VFLIP     false
#define CAM_HMIRROR   false

// ESP32-S3 boards (XIAO Sense, ESP32-S3 CAM): find the faces here and send the Pi only where
// they are (http://<camera>:82/faces). Much less lag than the Pi searching the stream, and
// the Pi stays free. The ESP32-CAM cannot, and ignores this.
#define CAM_DETECT_FACES true

// The detector only finds upright faces. If the camera is mounted on its side or upside
// down, turn the picture before searching it: 0, 90, 180 or 270 degrees clockwise.
// (Also from /control?var=rotate&val=90 until the next reboot.)
#define CAM_ROTATE    0
