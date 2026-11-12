idf_component_register(SRCS "main.c" "net.c" "web.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_http_server esp_wifi esp_netif esp_event esp_timer nvs_flash r2_detect)
