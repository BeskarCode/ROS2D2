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

// --- the LED face -------------------------------------------------------------------------------
module lp_holes(extra = 0) {
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) translate([-1, w[1], w[2]]) rotate([0, 90, 0])
        cylinder(d = lp_hole + extra, h = wall + 2, $fn = 32);
}

// names on the face, in its outside view: u = -Y (to the right seen from outside), v = Z.
// VL to the right of their dots (towards the front), US and PWR to the left (towards the back)
module lp_labels_2d() {
    r = lp_hole / 2 + lp_label_gap;
    for (i = [0 : len(pico_leds) - 1]) let(n = pico_leds[i][0], w = led_world(i), vl = n[0] == "V")
        translate([vl ? -w[1] + r : -w[1] - r, w[2]])
            text(n, size = lp_label_h, font = lp_label_font, halign = vl ? "left" : "right", valign = "center");
}
module lp_labels(depth = logo_depth) {
    multmatrix([[0, 0, -1, depth], [-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(depth) lp_labels_2d();
}
