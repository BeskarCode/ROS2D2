// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The HDMI on the back, without reprinting the base. The base already has the jack's window (hdmi_body + 0.6)
// and two M3 inserts hdmi_pitch apart. Two small parts screw onto them from outside:
//   hdmi_holder: a hood that holds the "A Female" end of an FPV FPC HDMI kit (micro-HDMI 90° plug + flat
//                 ribbon + HDMI A female board). The board slides into the hood from the wall side, the ribbon
//                 goes into the box through the window, under the Pi, to its micro-HDMI 0.
//   hdmi_cover:    a blank cover when no HDMI is fitted, with a plug that fills the window.
// Both with 2 × M3 × 8 countersunk (ISO 10642). Measure the A Female board when it arrives and set fpc_a.
include <params.scad>

fpc_a = [17, 8, 21];          // the A Female board: width (X), height (Z), length from its jack's mouth to its back (Y)
fpc_a_jack = [15.2, 6.2];     // its jack's metal shell, seen from the front
fpc_fit = 0.3;                // clearance per side
hood_wall = 1.8;
hood_lip = 1.6;               // in front of the board: the mouth holds it in when the plug is pulled
hdmi_plate_t = 3;             // the plate on the back, countersinks for the screws
hdmi_plate_h = 12;
cover_plug = 1.8;             // the cover's plug into the window (the back is wall = 2.5 thick)

function hdmi_plate_w() = hdmi_pitch + 8;
function hood_outer() = [fpc_a[0] + 2 * (fpc_fit + hood_wall), fpc_a[2] + fpc_fit + hood_lip, fpc_a[1] + 2 * (fpc_fit + hood_wall)];
function hdmi_screw_x() = [for (s = [-1, 1]) hdmi_c[0] + s * hdmi_pitch / 2];
// the hood must leave the screw axes free for the key: 1.5 mm from each axis to the hood's side
assert(hood_outer()[0] <= hdmi_pitch - 3, "fpc_a too wide: the hood would cover the screws");

module hdmi_plate(h) {
    difference() {
        translate([hdmi_c[0] - hdmi_plate_w() / 2, D, hdmi_c[1] - h / 2]) cube([hdmi_plate_w(), hdmi_plate_t, h]);
        for (x = hdmi_screw_x()) translate([x, D - 0.01, hdmi_c[1]]) rotate([-90, 0, 0]) {
            cylinder(d = m3_clear, h = hdmi_plate_t + 1, $fn = 24);
            translate([0, 0, hdmi_plate_t - (m3_head_d - m3_clear) / 2 + 0.02])
                cylinder(d1 = m3_clear, d2 = m3_head_d, h = (m3_head_d - m3_clear) / 2, $fn = 32);
        }
    }
}

module hdmi_holder() {
    o = hood_outer();
    difference() {
        union() {
            hdmi_plate(max(hdmi_plate_h, o[2]));
            translate([hdmi_c[0] - o[0] / 2, D, hdmi_c[1] - o[2] / 2]) cube(o);
        }
        // the board's pocket, open towards the wall
        translate([hdmi_c[0] - fpc_a[0] / 2 - fpc_fit, D - 0.01, hdmi_c[1] - fpc_a[1] / 2 - fpc_fit])
            cube([fpc_a[0] + 2 * fpc_fit, fpc_a[2] + fpc_fit + 0.01, fpc_a[1] + 2 * fpc_fit]);
        // the mouth: the jack's shell shows through, the board stays behind the lip
        translate([hdmi_c[0] - fpc_a_jack[0] / 2 - fpc_fit, D + o[1] - hood_lip - 0.01, hdmi_c[1] - fpc_a_jack[1] / 2 - fpc_fit])
            cube([fpc_a_jack[0] + 2 * fpc_fit, hood_lip + 0.02, fpc_a_jack[1] + 2 * fpc_fit]);
    }
}

module hdmi_cover() {
    hdmi_plate(hdmi_plate_h);
    translate([hdmi_c[0] - hdmi_body[0] / 2, D - cover_plug, hdmi_c[1] - hdmi_body[1] / 2])   // window minus 0.3 per side
        cube([hdmi_body[0], cover_plug + 0.01, hdmi_body[1]]);
}

// print orientation: the face that goes against the back down on the bed (the cover: its outer face)
module print_hdmi_holder() { translate([0, 0, -D]) rotate([90, 0, 0]) children(); }               // y = D -> z = 0, hood up
module print_hdmi_cover() { translate([0, 0, D + hdmi_plate_t]) rotate([-90, 0, 0]) children(); }   // outer face down, plug up

// for the tests: the screw shanks (M3, 0.1 under the clearance) and the room the key needs in front of them
module hdmi_screw_axes() {
    for (x = hdmi_screw_x()) translate([x, D - 1, hdmi_c[1]]) rotate([-90, 0, 0]) {
        cylinder(d = m3_clear - 0.2, h = 20, $fn = 24);
        translate([0, 0, 1 + hdmi_plate_t + 0.05]) cylinder(d = 3, h = 40, $fn = 24);   // 2.5 mm hex key, in front of the head
    }
}
