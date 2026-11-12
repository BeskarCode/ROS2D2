// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// r2_domecam_p4: the dome camera on a Waveshare ESP32-P4-WIFI6 + OV5647. Finds the faces or a
// colour itself and sends the Pi only where they are; video only while someone tunes it.
#include <stdio.h>

#include "esp_log.h"
#include "net.h"
#include "nvs_flash.h"
#include "web.h"

static const char *TAG = "r2_domecam_p4";

static int add_sensor(char *out, size_t size) {   // until the camera is in (Task 3)
  return snprintf(out, size, ",\"sensor\":\"none\"");
}

void app_main(void) {
  ESP_LOGI(TAG, "r2_domecam_p4");
  esp_err_t err = nvs_flash_init();   // the WiFi driver keeps its calibration here
  if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    nvs_flash_erase();
    nvs_flash_init();
  }
  net_start();
  web_register_status(add_sensor);
  if (!web_start()) ESP_LOGE(TAG, "web server did not start");
}
