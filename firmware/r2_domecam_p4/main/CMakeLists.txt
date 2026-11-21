idf_component_register(SRCS "main.c" "net.c" "web.c" "camera.c" "stream.c" "detect.cpp" "diag.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_http_server esp_wifi esp_netif esp_event esp_timer nvs_flash esp_driver_ppa esp_driver_jpeg esp_driver_tsens esp_app_format r2_detect)
