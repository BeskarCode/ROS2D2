# Plain C, no ESP-IDF dependencies: also built on the PC by test/cbuild.py
idf_component_register(SRCS "color_detect.c" INCLUDE_DIRS ".")
