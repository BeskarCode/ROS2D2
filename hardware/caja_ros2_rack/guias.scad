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
        cylinder(d = lp_hole + extra, h = lp_hole_x + 1, $fn = 32);
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

// --- the translucent piece (optional) ----------------------------------------------------------------
function lp_frame_x() = wall + lp_frame_gap;
function lp_ear_y(side) = side == 0 ? [lp_vl_strip[0], lp_vl_strip[0] + lp_ear[0]] : [lp_us_strip[1] - lp_ear[0], lp_us_strip[1]];

module lp_box(y, z, x0, x1) { translate([x0, y[0], z[0]]) cube([x1 - x0, y[1] - y[0], z[1] - z[0]]); }

// assembled: rods from the outside face to 0.5 mm over their LEDs, the frame on the wall's inside face
module guias_luz() {
    x0 = lp_frame_x(); x1 = x0 + lp_frame_t;
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) translate([0, w[1], w[2]]) rotate([0, 90, 0])
        cylinder(d = lp_d, h = lp_tip_x(), $fn = 32);
    lp_box(lp_vl_strip, lp_strip_z, x0, x1);
    lp_box(lp_us_strip, lp_strip_z, x0, x1);
    lp_box([lp_vl_strip[0], lp_us_strip[1]], lp_bar_z, x0, x0 + lp_bar_t);
    p = led_world(len(pico_leds) - 1);
    lp_box(lp_pwr_arm, [p[2] - lp_d / 2, lp_bar_z[1]], x0, x1);
    for (side = [0, 1], z = lp_hooks_z[side])                        // the ears the hooks catch
        lp_box(lp_ear_y(side), [z - lp_ear[1] / 2, z + lp_ear[1] / 2], x0, lp_ear[2]);
}

// on the wall, beside each ear: a post whose lip snaps over the ear's top (chamfered on top so the piece
// pushes it aside going in). Only on the LED face.
module lp_hooks() {
    for (side = [0, 1], z = lp_hooks_z[side]) let(
        e = lp_ear_y(side), s = side == 0 ? -1 : 1,                  // the post stands outside the frame
        py = side == 0 ? e[0] - lp_hook_gap - lp_hook_t : e[1] + lp_hook_gap,
        lx0 = lp_ear[2] + lp_hook_air, lx1 = lx0 + lp_hook_lip_h,
        tip = side == 0 ? e[0] + lp_hook_lip : e[1] - lp_hook_lip,
        root = side == 0 ? py + lp_hook_t : py)
        translate([0, 0, z - lp_ear[1] / 2]) linear_extrude(lp_ear[1]) union() {
            translate([wall - 0.01, py]) square([lx1 - wall + 0.01, lp_hook_t]);
            let(o = side == 0 ? py : py + lp_hook_t)                  // root chamfer, on the side away from the frame
                polygon([[wall - 0.01, o], [wall - 0.01, o + s * lp_hook_root], [wall + lp_hook_root, o]]);
            polygon([[lx0, root], [lx0, tip], [lx1, root]]);         // lip, sloped towards +X
        }
}

module print_guias() { rotate([0, -90, 0]) children(); }            // outer ends on the bed, rods up
