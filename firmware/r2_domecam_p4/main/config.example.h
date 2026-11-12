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

// Video for the console (only sent while someone watches it): width 320, 640, 800 or 1280
// (the height keeps 4:3) and JPEG quality 1 (smallest) .. 100 (best).
// (Also from /control?var=framesize|quality&val=N until the next reboot.)
#define CAM_STREAM_WIDTH 640
#define CAM_JPEG_QUALITY 70

// Mounting: fix a camera that sees the world upside down, mirrored or on its side.
// CAM_ROTATE turns the picture clockwise: 0, 90, 180 or 270. The face finder only finds upright
// faces, so turn it until they are. (Also from /control?var=vflip|hmirror|rotate&val=N.)
#define CAM_VFLIP   false
#define CAM_HMIRROR false
#define CAM_ROTATE  0

// Colour order of the pictures the detectors get. If a red shirt is found as blue (README.md,
// first test with the board), flip this.
#define CAM_RGB_SWAP false

// Look for faces on the camera from the start (the Pi switches to the colour and back with
// /control?var=detect&val=0|1|2). The faces go out on http://<camera>:82/faces.
#define CAM_DETECT_FACES true

// Picture width the detectors search: 320, 640, 800 or 1280 (the height keeps 4:3).
// Faces: bigger finds them farther away but slower; keep it at 10 pictures a second or more
// (/status faces_fps). A face of 16 cm at 4 m is about 30 px wide at 640.
// Colour: a shirt is big, 320 is plenty.
#define DETECT_FACE_WIDTH  640
#define DETECT_COLOR_WIDTH 320
