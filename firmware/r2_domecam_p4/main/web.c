// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
#include "web.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "net.h"

#define MAX_CONTROLS 40
#define MAX_STATUS 8

static struct {
  const char *var;
  int (*set)(int);
} s_controls[MAX_CONTROLS];
static int s_n_controls;
static int (*s_status[MAX_STATUS])(char *, size_t);
static int s_n_status;

void web_register_control(const char *var, int (*set)(int)) {
  if (s_n_controls < MAX_CONTROLS) s_controls[s_n_controls++] = (typeof(s_controls[0])){var, set};
}

void web_register_status(int (*add)(char *, size_t)) {
  if (s_n_status < MAX_STATUS) s_status[s_n_status++] = add;
}

static const char PAGE[] =
    "<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'>"
    "<title>r2_domecam_p4</title>"
    "<style>body{margin:0;background:#0d1117;color:#e6edf3;font:14px system-ui,sans-serif;text-align:center}"
    "img{max-width:100%;background:#000;margin-top:12px}pre{display:inline-block;text-align:left;color:#8b949e}</style>"
    "</head><body><h3 id=h>r2_domecam_p4</h3><img id=v alt='(no camera, or the stream is busy)'><br><pre id=s></pre>"
    "<script>const host=location.hostname;document.getElementById('v').src='http://'+host+':81/stream';"
    "async function st(){try{const j=await(await fetch('/status')).json();"
    "document.getElementById('h').textContent=j.name+' - '+j.ip;"
    "document.getElementById('s').textContent=JSON.stringify(j,null,1);}catch(e){}}"
    "st();setInterval(st,2000);</script></body></html>";

static esp_err_t page_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_sendstr(req, PAGE);
}

static esp_err_t status_handler(httpd_req_t *req) {
  char json[1024];
  int n = snprintf(json, sizeof(json),
                   "{\"name\":\"%s\",\"ip\":\"%s\",\"rssi\":%d,\"board\":\"esp32p4\",\"uptime_s\":%lu,"
                   "\"heap\":%u,\"psram_free\":%u",
                   CAM_HOSTNAME, net_ip(), net_rssi(), (unsigned long)(esp_timer_get_time() / 1000000),
                   (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
                   (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  for (int i = 0; i < s_n_status && n < (int)sizeof(json) - 2; i++) n += s_status[i](json + n, sizeof(json) - 2 - n);
  json[n++] = '}';
  json[n] = 0;
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, json);
}

static esp_err_t control_handler(httpd_req_t *req) {
  char query[96], var[32], val[16];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK ||
      httpd_query_key_value(query, "var", var, sizeof(var)) != ESP_OK ||
      httpd_query_key_value(query, "val", val, sizeof(val)) != ESP_OK) {
    char list[400] = "use ?var=";
    for (int i = 0; i < s_n_controls; i++)
      if (s_controls[i].set) {
        strlcat(list, s_controls[i].var, sizeof(list));
        strlcat(list, "|", sizeof(list));
      }
    strlcat(list, "&val=N", sizeof(list));
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, list);
  }
  char *end;
  long v = strtol(val, &end, 10);
  for (int i = 0; i < s_n_controls; i++) {
    if (strcmp(var, s_controls[i].var)) continue;
    if (!s_controls[i].set) return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "not on the ESP32-P4");
    if (*end || end == val || s_controls[i].set((int)v) != 0)
      return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "value out of range");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_sendstr(req, "OK");
  }
  return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "unknown var");
}

httpd_handle_t web_start_port(int port, int ctrl_port) {
  httpd_handle_t h = NULL;
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = port;
  cfg.ctrl_port = ctrl_port;
  cfg.core_id = 0;   // web servers with the WiFi on core 0: core 1 is the detector's
  cfg.lru_purge_enable = true;
  return httpd_start(&h, &cfg) == ESP_OK ? h : NULL;
}

httpd_handle_t web_start(void) {
  httpd_handle_t h = web_start_port(80, 32768);
  if (!h) return NULL;
  const httpd_uri_t uris[] = {
      {.uri = "/", .method = HTTP_GET, .handler = page_handler},
      {.uri = "/status", .method = HTTP_GET, .handler = status_handler},
      {.uri = "/control", .method = HTTP_GET, .handler = control_handler},
  };
  for (size_t i = 0; i < sizeof(uris) / sizeof(uris[0]); i++) httpd_register_uri_handler(h, &uris[i]);
  return h;
}
