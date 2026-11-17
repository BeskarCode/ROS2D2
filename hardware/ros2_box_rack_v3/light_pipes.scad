// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Light pipes: the Pico board's 10 LEDs and the Pico's own seen from outside the main face. The LED face (wall_led) prints
// a dark tube from each hole to just over its LED, so the light is not lost on the way; outside, a thin
// translucent lens presses into a recess at the mouth of each tube, flush with the face.
include <params.scad>

function led_world(i) = pico2world(pico_leds[i][1], pico_leds[i][2]) - [led_base(pico_leds[i]), 0, 0];
function lp_tip_x() = pico_x() - led_h - led_air;       // where a tube ends, over its LED
function lp_narrow_x() = pico_x() - oled_thick - 0.5;   // from here on the tube is thinner: the board's low parts

// --- the LED face: tubes, bores and lens recesses -------------------------------------------------
module lp_at(i) { w = led_world(i); translate([0, w[1], w[2]]) rotate([0, 90, 0]) children(); }   // +Z -> +X

module lp_tubes() {
    for (i = [0 : len(pico_leds) - 1]) if (led_tube(pico_leds[i])) lp_at(i) {
        translate([0, 0, wall - 0.01]) cylinder(d = lp_tube_od, h = lp_narrow_x() - wall + 0.01, $fn = 40);
        translate([0, 0, lp_narrow_x() - 0.01]) cylinder(d = lp_tip_od, h = lp_tip_x() - lp_narrow_x() + 0.01, $fn = 32);
    }
}

// extra: grows every cut (clearance checks)
module lp_holes(extra = 0) {
    for (i = [0 : len(pico_leds) - 1]) lp_at(i) {
        if (led_tube(pico_leds[i])) {
            translate([0, 0, -1]) cylinder(d = lp_bore + extra, h = lp_narrow_x() + 1.01, $fn = 32);
            translate([0, 0, lp_narrow_x()]) cylinder(d = lp_tip_bore + extra, h = lp_tip_x() - lp_narrow_x() + 1, $fn = 32);
        } else translate([0, 0, -1]) cylinder(d = lp_bore + extra, h = wall + 2, $fn = 32);   // straight through the face
        translate([0, 0, -1]) cylinder(d = lp_hole + extra, h = lp_lens_t + 1.05, $fn = 48);  // the lens recess, 0.05 deeper
        translate([0, 0, -0.01]) cylinder(d1 = lp_hole + 2 * lp_chamfer + 0.02 + extra, d2 = lp_hole + extra, h = lp_chamfer + 0.01, $fn = 48);
    }
}

// --- the lenses (translucent): a thin disc flush with the face and a stem pressed into the tube ----------
module lente() {
    cylinder(d = lp_lens_d, h = lp_lens_t, $fn = 48);
    cylinder(d = lp_stem_d, h = lp_lens_t + lp_stem_l, $fn = 32);
}
module lentes_montadas() { for (i = [0 : len(pico_leds) - 1]) lp_at(i) lente(); }
// to print: discs on the bed (the face that shows comes out smooth), 11 + 2 spares
module led_lenses() { for (k = [0 : lp_lens_n - 1]) translate([(k % 4) * 9, floor(k / 4) * 9, 0]) lente(); }
