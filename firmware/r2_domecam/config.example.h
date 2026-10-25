// r2_domecam settings. Copy this file to config.h and fill it in:
// config.h stays on your computer (it is in .gitignore), so the WiFi password is never pushed.
#pragma once

// Board: uncomment the one you have
#define BOARD_XIAO_ESP32S3_SENSE      // Seeed XIAO ESP32S3 Sense + OV2640
// #define BOARD_ESP32_CAM            // AI-Thinker ESP32-CAM (the common one) + OV2640

// WiFi (hidden networks work too)
#define WIFI_SSID     "your-network"
#define WIFI_PASSWORD "your-password"

// Name on the network: http://r2-domecam1.local/ . Use r2-domecam2, 3... for more cameras.
#define CAM_HOSTNAME  "r2-domecam1"

// Picture sent to the Pi. The face detector works at 320 px wide, so QVGA is enough and
// fastest; VGA gives a sharper picture for the web console at fewer frames per second.
//   FRAMESIZE_QVGA  320x240     FRAMESIZE_VGA  640x480     FRAMESIZE_SVGA 800x600
#define CAM_FRAMESIZE FRAMESIZE_VGA
#define CAM_QUALITY   12      // JPEG quality 4 (best, bigger) .. 63 (worst, smaller)

// Mounting: the OV2640 on the Sense board sees the world upside down or mirrored
// depending on how it sits in the dome. Fix it here (or later from /control).
#define CAM_VFLIP     false
#define CAM_HMIRROR   false
