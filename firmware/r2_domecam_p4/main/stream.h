// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// /capture (one JPEG) on port 80 and :81/stream (MJPEG, only while someone watches).
#pragma once
#include "esp_http_server.h"

void stream_start(httpd_handle_t web);
int stream_clients(void);
