// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "diag.h"

#include <stdio.h>

#include "driver/temperature_sensor.h"
#include "esp_app_desc.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "net.h"
#include "nvs.h"
#include "web.h"

static const char *TAG = "diag";
static uint32_t s_boots;
static temperature_sensor_handle_t s_temp;
static volatile float s_temp_c = -1000, s_load[2] = {-1, -1};

static const char *reset_text(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "power on";
    case ESP_RST_EXT: return "reset pin";
    case ESP_RST_SW: return "restart";
    case ESP_RST_PANIC: return "crash";
    case ESP_RST_INT_WDT: return "watchdog (interrupt)";
    case ESP_RST_TASK_WDT: return "watchdog (task)";
    case ESP_RST_WDT: return "watchdog";
    case ESP_RST_DEEPSLEEP: return "deep sleep";
    case ESP_RST_BROWNOUT: return "brownout (low power)";
    case ESP_RST_SDIO: return "SDIO";
    case ESP_RST_USB: return "USB (flashing)";
    case ESP_RST_JTAG: return "JTAG";
    case ESP_RST_EFUSE: return "efuse";
    case ESP_RST_PWR_GLITCH: return "power glitch";
    case ESP_RST_CPU_LOCKUP: return "CPU lockup";
    default: return "unknown";
  }
}

// How busy each core was in the last second: 100 % minus its idle task's share of the time
static void sample(void *arg) {
  static uint32_t last_idle[2], last_us;
  uint32_t now = (uint32_t)esp_timer_get_time();   // the run time counter is esp_timer microseconds
  uint32_t span = now - last_us;
  for (int c = 0; c < 2; c++) {
    uint32_t idle = (uint32_t)ulTaskGetIdleRunTimeCounterForCore(c);
    if (last_us && span) {
      float busy = 100.0f - 100.0f * (float)(idle - last_idle[c]) / (float)span;
      s_load[c] = busy < 0 ? 0 : busy > 100 ? 100 : busy;
    }
    last_idle[c] = idle;
  }
  last_us = now;
  float t;
  if (s_temp && temperature_sensor_get_celsius(s_temp, &t) == ESP_OK) s_temp_c = t;
}

static int add_status(char *out, size_t size) {
  const esp_app_desc_t *app = esp_app_get_description();
  int n = snprintf(out, size, ",\"fw\":\"%s\",\"built\":\"%s %s\",\"reset_reason\":\"%s\",\"boots\":%lu,"
                   "\"wifi_reconnects\":%lu,\"wifi_last_reason\":%d",
                   app->version, app->date, app->time, reset_text(esp_reset_reason()), (unsigned long)s_boots,
                   (unsigned long)net_reconnects(), net_last_reason());
  if (n < 0 || n >= (int)size) return 0;
  int m = s_temp_c > -999 ? snprintf(out + n, size - n, ",\"temp_c\":%.1f", s_temp_c)
                          : snprintf(out + n, size - n, ",\"temp_c\":null");
  if (m < 0 || n + m >= (int)size) return n;
  n += m;
  m = s_load[0] >= 0 ? snprintf(out + n, size - n, ",\"cpu\":[%.0f,%.0f]", s_load[0], s_load[1])
                     : snprintf(out + n, size - n, ",\"cpu\":null");
  return m < 0 || n + m >= (int)size ? n : n + m;
}

void diag_start(void) {
  nvs_handle_t h;
  if (nvs_open("diag", NVS_READWRITE, &h) == ESP_OK) {   // how many times it has started, ever
    nvs_get_u32(h, "boots", &s_boots);
    s_boots++;
    nvs_set_u32(h, "boots", s_boots);
    nvs_commit(h);
    nvs_close(h);
  }
  ESP_LOGI(TAG, "start #%lu, reset reason: %s", (unsigned long)s_boots, reset_text(esp_reset_reason()));
  temperature_sensor_config_t tc = TEMPERATURE_SENSOR_CONFIG_DEFAULT(-10, 80);
  if (temperature_sensor_install(&tc, &s_temp) != ESP_OK || temperature_sensor_enable(s_temp) != ESP_OK) {
    ESP_LOGW(TAG, "no chip temperature");
    s_temp = NULL;
  }
  const esp_timer_create_args_t a = {.callback = sample, .name = "diag"};
  esp_timer_handle_t t;
  if (esp_timer_create(&a, &t) == ESP_OK) esp_timer_start_periodic(t, 1000000);
  web_register_status(add_status);
}
