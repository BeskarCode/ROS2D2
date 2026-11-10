// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The base, assembled position: floor + back panel + the Pi's bracket + the converter's bosses +
// the ears that fix the box to the R2. The front screws to it from under the floor; the U shell
// slides down over it and screws into the side bosses.
include <params.scad>

port_margin = 0.5;                 // round the Pi's jacks in the back cut-out
standoff_d = 5.5;                  // Pi standoffs (the ghost keeps a 6 mm clear zone)
ear = [12, 14];                    // mounting ear: out from the side x along Y
shell_boss = [8, 10, 9.5];         // X x Y x Z block on the floor, insert along X
function shell_screw_y() = shell_screw_ys;
function shell_screw_z() = wall + shell_boss[2] / 2;

module floor_plate() {
    translate([0, wall + fit, 0]) cube([W, D - wall - fit, wall]);
}

module back_panel() {
    translate([0, D - wall, 0]) cube([W, wall, H]);
}

module countersunk(l = 20) {       // along +Y from y = 0 (outer face), M3 flat head
    rotate([-90, 0, 0]) {
        translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2, $fn = 32);
        cylinder(d = m3_clear, h = l, $fn = 24);
    }
}

module back_cuts() {
    yb = D - wall;
    // Pi jacks, pushed out through the wall
    minkowski() { pi_ports(10); cube(2 * port_margin, center = true); }
    // XT60E-F: body + 2 countersunk screws from outside, holes along Z
    translate([xt60_c[0] - xt60_body[0] / 2, yb - 1, xt60_c[1] - xt60_body[1] / 2])
        cube([xt60_body[0], wall + 2, xt60_body[1]]);
    for (s = [-1, 1]) translate([xt60_c[0], yb - 1, xt60_c[1] + s * xt60_hole_pitch / 2])
        rotate([-90, 0, 0]) cylinder(d = m3_clear, h = wall + 2, $fn = 24);   // the flange is countersunk, not the wall
    // KCD1 rocker
    translate([sw_c[0] - sw_cut[0] / 2, yb - 1, sw_c[1] - sw_cut[1] / 2]) cube([sw_cut[0], wall + 2, sw_cut[1]]);
    translate([sw_c[0] - sw_cut[0] / 2 - 3, yb - 0.01, sw_c[1] - sw_cut[1] / 2 - 3])      // thinner round it, for the clips
        cube([sw_cut[0] + 6, wall - sw_panel_t + 0.01, sw_cut[1] + 6]);
    // sensor cable slot, round ends (for a grommet strip)
    translate([sensor_slot_c[0], yb - 1, sensor_slot_c[1]]) rotate([-90, 0, 0])
        hull() for (s = [-1, 1]) translate([s * (sensor_slot[0] - sensor_slot[1]) / 2, 0, 0])
            cylinder(d = sensor_slot[1], h = wall + 2, $fn = 32);
    // a small vent between the switch/slot and the Pi
    for (i = [0 : 4]) translate([54 + i * 4, yb - 1, 40]) cube([2, wall + 2, 45]);
}

module pi_bracket(extra = 0) {
    y0 = pi_y0(); z0 = pi_z0();
    difference() {
        translate([bracket_x(), y0 - 2, wall]) cube([bracket_t, D - wall - (y0 - 2), z0 + pi_w + 2 - wall]);
        right_low_vents();      // the shell's low vents on the right stay open through the bracket
    }
    // standoffs from the bracket to the Pi's solder side
    for (h = pi_holes) translate([bracket_x() + 0.01, y0 + h[0], z0 + h[1]])
        rotate([0, -90, 0]) difference() {
            cylinder(d = standoff_d, h = standoff_pi - 0.05 + extra + 0.01, $fn = 32);
            translate([0, 0, 1]) cylinder(d = m25_hole, h = standoff_pi + 1, $fn = 20);
        }
}

module right_low_vents(x_in = 12) {
    for (y = side_slots_y()) translate([W - x_in, y, side_band_low[0]])
        cube([x_in + 1, slot_w, side_band_low[1] - side_band_low[0]]);
}

module conv_insert_holes() {
    for (h = conv_holes) translate([conv_pos[0] + h[0], conv_pos[1] + h[1], wall + conv_lift - insert_h + 0.01])
        cylinder(d = insert_d, h = insert_h, $fn = 24);
}

module conv_bosses() {
    difference() {
        for (h = conv_holes) translate([conv_pos[0] + h[0], conv_pos[1] + h[1], wall - 0.01])
            cylinder(d = boss_d, h = conv_lift + 0.01, $fn = 32);
        conv_insert_holes();
    }
}

// blocks on the floor the U shell screws into (insert along X, from the outside)
module shell_bosses() {
    for (y = shell_screw_y()) for (side = [0, 1]) {
        x = side == 0 ? wall + fit : W - wall - fit - shell_boss[0];
        translate([x, y - shell_boss[1] / 2, wall - 0.01]) difference() {
            cube([shell_boss[0], shell_boss[1], shell_boss[2] + 0.01]);
            translate([side == 0 ? -0.01 : shell_boss[0] - insert_h + 0.01, shell_boss[1] / 2, shell_boss[2] / 2])
                rotate([0, 90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
        }
    }
}

module mount_ears() {
    for (x = [-ear[0], W]) for (y = [wall + 4, D - ear[1] - 4]) translate([x, y, 0])
        difference() {
            hull() {                       // flush with the floor: the shell's sides sit on it
                translate([x < 0 ? ear[0] - 1 : 0, 0, 0]) cube([1, ear[1], wall]);
                translate([ear[0] / 2, ear[1] / 2, 0]) cylinder(d = ear[0], h = wall, $fn = 40);
            }
            translate([ear[0] / 2, ear[1] / 2, -0.01]) cylinder(d = mount_d, h = wall + 2, $fn = 24);
        }
}

// floor holes for the front's tabs (screws from below, countersunk)
module front_tab_holes() {
    for (x = front_tabs_x()) translate([x, wall + front_tab[1] / 2 + 0.5, 0])
        rotate([90, 0, 0]) translate([0, 0, 0]) rotate([-90, 0, 0]) {
            translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2, $fn = 32);
            cylinder(d = m3_clear, h = wall + 1, $fn = 24);
        }
}

module base(ears = true) {
    difference() {
        union() {
            floor_plate();
            back_panel();
            pi_bracket();
            conv_bosses();
            shell_bosses();
            if (ears) mount_ears();
            top_tab(top_tab_y()[1], gusset = 1);
        }
        back_cuts();
        front_tab_holes();
    }
}
