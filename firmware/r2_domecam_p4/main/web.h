// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#pragma once
#include <stddef.h>
#include "esp_http_server.h"

// Port 80: / (a page to look at the camera), /status (JSON), /control?var=X&val=N.
httpd_handle_t web_start(void);

// A /control variable. set(val) returns 0 when done, -1 when val is out of range (-> 400).
// set NULL: a variable of the ESP32-S3 camera that the P4 does not have (-> 400 with a reason).
void web_register_control(const char *var, int (*set)(int val));

// Adds fields to /status: write ',"key":value' pairs into out and return the length written.
void web_register_status(int (*add)(char *out, size_t size));

// Small helpers for the other servers (:81, :82)
httpd_handle_t web_start_port(int port, int ctrl_port);
