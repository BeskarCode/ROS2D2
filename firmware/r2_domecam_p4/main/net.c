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
static volatile unsigned long s_reconnects;
static volatile int s_last_reason;
static TimerHandle_t s_retry;   // reconnects after a short pause, not in a tight loop
static esp_netif_t *s_sta;

#ifndef CAM_STATIC_IP
#define CAM_STATIC_IP ""
#endif

static void retry(TimerHandle_t t) { esp_wifi_connect(); }

// A fixed address (CAM_STATIC_IP): the Pi finds the camera at once after a drop, without waiting
// for mDNS to answer again (it took up to 90 s). Outside the Pi's DHCP pool (10.42.0.11-50).
static void use_static_ip(void) {
  esp_netif_ip_info_t ip = {0};
  if (!CAM_STATIC_IP[0] || esp_netif_str_to_ip4(CAM_STATIC_IP, &ip.ip) != ESP_OK) return;
  esp_netif_set_ip4_addr(&ip.netmask, 255, 255, 255, 0);
  ip.gw.addr = (ip.ip.addr & 0x00FFFFFF) | (1u << 24);   // x.y.z.1: the Pi
  esp_netif_dhcpc_stop(s_sta);
  if (esp_netif_set_ip_info(s_sta, &ip) != ESP_OK) {
    ESP_LOGW(TAG, "could not set %s, using DHCP", CAM_STATIC_IP);
    esp_netif_dhcpc_start(s_sta);
  }
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data) {
  if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
    esp_wifi_connect();
  } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_CONNECTED) {
    use_static_ip();
  } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
    // The Pi rebooted or the droid went out of range: keep trying forever, so the dome
    // camera always comes back without anyone touching it. Why and how often goes to /status.
    wifi_event_sta_disconnected_t *e = (wifi_event_sta_disconnected_t *)data;
    if (s_connected) {
      s_reconnects++;
      s_last_reason = e->reason;
      ESP_LOGW(TAG, "WiFi lost (reason %d, rssi %d), reconnecting", e->reason, e->rssi);
    }
    s_connected = false;
    strcpy(s_ip, "0.0.0.0");
    if (!s_retry || xTimerStart(s_retry, 0) != pdPASS) esp_wifi_connect();
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
  s_sta = sta;
  esp_netif_set_hostname(sta, CAM_HOSTNAME);
  s_retry = xTimerCreate("wifi_retry", pdMS_TO_TICKS(500), pdFALSE, NULL, retry);
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
  ESP_LOGI(TAG, "Connecting to %s%s%s", WIFI_SSID, CAM_STATIC_IP[0] ? " as " : "", CAM_STATIC_IP);

  if (mdns_init() == ESP_OK) {
    mdns_hostname_set(CAM_HOSTNAME);
    mdns_service_add(NULL, "_http", "_tcp", 80, NULL, 0);
  }
}

bool net_connected(void) { return s_connected; }
const char *net_ip(void) { return s_ip; }

unsigned long net_reconnects(void) { return s_reconnects; }
int net_last_reason(void) { return s_last_reason; }

int net_rssi(void) {
  wifi_ap_record_t ap;
  return s_connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK ? ap.rssi : 0;
}
