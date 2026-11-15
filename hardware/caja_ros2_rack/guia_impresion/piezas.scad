// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Images for the rack box's print guide: each printable file, from its STL, in its print colours.
//   openscad -o pared_monocolor.png -D 'pieza="pared_monocolor"' piezas.scad
pieza = "pared_multicolor";

WHITE = [0.95, 0.95, 0.93];  NAVY = [0.11, 0.16, 0.42];  BLUE = [0.16, 0.46, 0.86];  GREY = [0.55, 0.55, 0.58];
LENS = [0.80, 0.90, 1.00];   ROD = [1, 0.55, 0.1];

module s(f, c) color(c) import(str("../stl/", f, ".stl"), convexity = 6);
module logo(sfx = "", dir = "") { s(str(dir, "logo_marino", sfx), NAVY); s(str(dir, "logo_azul", sfx), BLUE); s(str(dir, "logo_gris", sfx), GREY); }

H = 145;   // the box's height (params.scad): undoes print_pared(), the walls stand as mounted, face to -X
module montada() rotate([0, 90, 0]) translate([-H, 0, 0]) children();

if (pieza == "pared_multicolor") montada() { s("pared", WHITE); logo(); }
else if (pieza == "pared_monocolor") montada() s("pared_monocolor", WHITE);
else if (pieza == "pared_led_multicolor") montada() { s("con_leds/pared_led", WHITE); logo("_led", "con_leds/"); }
else if (pieza == "pared_led_monocolor") montada() s("con_leds/pared_led_monocolor", WHITE);
else if (pieza == "pared_led_sin_ams") montada() s("sin_ams/pared_led_sin_ams", WHITE);
else if (pieza == "rellenos") montada() { s("sin_ams/relleno_marino", NAVY); s("sin_ams/relleno_azul", BLUE); s("sin_ams/relleno_gris", GREY); }
else if (pieza == "lentes_led") s("con_leds/lentes_led", LENS);
else if (pieza == "pulsador") s("pulsador", ROD);
else s(pieza, WHITE);       // base, tapa, marco_pi4, marco_pi5, soporte_hdmi, tapa_hdmi
