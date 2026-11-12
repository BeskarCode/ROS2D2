// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Light pipes: the Pico board's 10 LEDs seen from outside the main face. The LED face (pared_led) has a
// hole over each LED; the translucent piece (optional) puts a rod in each hole, held by the wall, never
// touching the board.
include <params.scad>

function led_world(i) = pico2world(pico_leds[i][1], pico_leds[i][2]);
function lp_tip_x() = pico_x() - led_h - led_air;       // where a rod ends, over its LED

// one loose rod to check the filament lets enough light through: print it standing, hold it on a lit LED
module prueba_luz() {
    cylinder(d = 8, h = 1.5, $fn = 40);                 // grip, at the outer end
    cylinder(d = lp_d, h = lp_tip_x(), $fn = 32);
}
