// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#pragma once
#include <stdbool.h>

// WiFi through the ESP32-C6 (esp_hosted), reconnecting by itself, and mDNS as CAM_HOSTNAME.
void net_start(void);
bool net_connected(void);
const char *net_ip(void);   // "0.0.0.0" while not connected
int net_rssi(void);         // dBm, 0 while not connected
