// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "net.h"

#include <stdio.h>
#include <string.h>

#include "config.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/timers.h"
#include "mdns.h"

static const char *TAG = "net";
static volatile bool s_connected;
static char s_ip[16] = "0.0.0.0";

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data) {
  if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
    esp_wifi_connect();
  } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
    // The Pi rebooted or the droid went out of range: keep trying forever, so the dome
    // camera always comes back without anyone touching it
    if (s_connected) ESP_LOGW(TAG, "WiFi lost, reconnecting");
    s_connected = false;
    strcpy(s_ip, "0.0.0.0");
    esp_wifi_connect();
  } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
    ip_event_got_ip_t *e = (ip_event_got_ip_t *)data;
    snprintf(s_ip, sizeof(s_ip), IPSTR, IP2STR(&e->ip_info.ip));
    s_connected = true;
    ESP_LOGI(TAG, "Connected to %s: http://%s/  stream http://%s:81/stream  faces http://%s:82/faces",
             WIFI_SSID, s_ip, s_ip, s_ip);
    ESP_LOGI(TAG, "Also http://%s.local/", CAM_HOSTNAME);
  }
}

void net_start(void) {
  ESP_ERROR_CHECK(esp_netif_init());
  ESP_ERROR_CHECK(esp_event_loop_create_default());
  esp_netif_t *sta = esp_netif_create_default_wifi_sta();
  esp_netif_set_hostname(sta, CAM_HOSTNAME);
  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&cfg));
  ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
  ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL));
  wifi_config_t wc = {0};
  strncpy((char *)wc.sta.ssid, WIFI_SSID, sizeof(wc.sta.ssid));
  strncpy((char *)wc.sta.password, WIFI_PASSWORD, sizeof(wc.sta.password));
  wc.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;   // hidden networks too
  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wc));
  ESP_ERROR_CHECK(esp_wifi_start());
  esp_wifi_set_ps(WIFI_PS_NONE);   // power saving adds tens of ms of lag per picture
  ESP_LOGI(TAG, "Connecting to %s", WIFI_SSID);

  if (mdns_init() == ESP_OK) {
    mdns_hostname_set(CAM_HOSTNAME);
    mdns_service_add(NULL, "_http", "_tcp", 80, NULL, 0);
  }
}

bool net_connected(void) { return s_connected; }
const char *net_ip(void) { return s_ip; }

int net_rssi(void) {
  wifi_ap_record_t ap;
  return s_connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK ? ap.rssi : 0;
}
