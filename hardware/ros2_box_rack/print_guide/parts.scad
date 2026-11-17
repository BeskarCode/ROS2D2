// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Images for the rack box's print guide: each printable file, from its STL, in its print colours.
//   openscad -o wall_monocolor.png -D 'pieza="wall_monocolor"' parts.scad
pieza = "wall_multicolor";

WHITE = [0.95, 0.95, 0.93];  NAVY = [0.11, 0.16, 0.42];  BLUE = [0.16, 0.46, 0.86];  GREY = [0.55, 0.55, 0.58];
LENS = [0.80, 0.90, 1.00];   ROD = [1, 0.55, 0.1];

module s(f, c) color(c) import(str("../stl/", f, ".stl"), convexity = 6);
module logo(sfx = "", dir = "") { s(str(dir, "logo_navy", sfx), NAVY); s(str(dir, "logo_blue", sfx), BLUE); s(str(dir, "logo_grey", sfx), GREY); }

H = 145;   // the box's height (params.scad): undoes print_pared(), the walls stand as mounted, face to -X
module montada() rotate([0, 90, 0]) translate([-H, 0, 0]) children();

if (pieza == "wall_multicolor") montada() { s("wall", WHITE); logo(); }
else if (pieza == "wall_monocolor") montada() s("wall_monocolor", WHITE);
else if (pieza == "wall_led_multicolor") montada() { s("leds/wall_led", WHITE); logo("_led", "leds/"); }
else if (pieza == "wall_led_monocolor") montada() s("leds/wall_led_monocolor", WHITE);
else if (pieza == "wall_led_no_ams") montada() s("no_ams/wall_led_no_ams", WHITE);
else if (pieza == "inlays") montada() { s("no_ams/inlay_navy", NAVY); s("no_ams/inlay_blue", BLUE); s("no_ams/inlay_grey", GREY); }
else if (pieza == "led_lenses") s("leds/led_lenses", LENS);
else if (pieza == "push_rod") s("push_rod", ROD);
else s(pieza, WHITE);       // base, tapa, frame_pi4, frame_pi5, hdmi_holder, hdmi_cover
