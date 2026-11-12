# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
# r2_domecam_p4: the dome camera on a Waveshare ESP32-P4-WIFI6 (ESP32-P4 + ESP32-C6) with an OV5647.
cmake_minimum_required(VERSION 3.16)

# ESP32-P4 chips v3.x and v1.x need different builds. v3.x by default (what Waveshare ships now);
# for a v1.x chip: idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;config/rev1.defaults" build
# (esptool.py chip_id prints the revision; see README.md)
if((NOT DEFINED SDKCONFIG_DEFAULTS OR SDKCONFIG_DEFAULTS STREQUAL "")
   AND (NOT DEFINED ENV{SDKCONFIG_DEFAULTS} OR "$ENV{SDKCONFIG_DEFAULTS}" STREQUAL ""))
  set(SDKCONFIG_DEFAULTS "sdkconfig.defaults;${CMAKE_CURRENT_LIST_DIR}/config/rev3.defaults")
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(r2_domecam_p4)
