// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The base: floor + back + the central divider (the Pi on standoffs, the converter on inserts) +
// floor bosses for the shell + ears for the R2. The main face screws to it from under the floor.
include <params.scad>

port_margin = 0.5;
standoff_d = 5.5;
ear = [14, 12];                                   // along X x out from the box (Y)
ear_x = [20, 60];
boss = [8, 10, 9.5];
boss_y = [15, 86];
div_top_y = [20, 75];
function div_cx() = (div_x[0] + div_x[1]) / 2;
function conv_insert_pos(h) = [div_x[1], conv_y + h[0], wall + h[1]];

module floor_plate() { translate([wall + fit, 0, 0]) cube([W - wall - fit, D, wall]); }
module back_panel() { translate([wall + fit, D - wall, 0]) cube([W - wall - fit, wall, H]); }

module divider() {
    difference() {
        translate([div_x[0], wall + fit, wall - 0.01]) cube([div_x[1] - div_x[0], D - 2 * wall - fit + 0.02, H - 2 * wall + 0.01]);   // top flush with the roof's underside
        translate([div_x[0] - 1, div_pass[0], wall - 0.1]) cube([div_x[1] - div_x[0] + 2, div_pass[1] - div_pass[0], div_pass[2]]);
    }
}

module pi_standoffs(extra = 0) {
    for (h = pi_holes) translate([div_x[1] - 0.01, pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, 90, 0])
        cylinder(d = standoff_d, h = standoff_pi - 0.05 + extra + 0.01, $fn = 32);
}
module pi_standoff_holes() {
    for (h = pi_holes) translate([div_x[1] - 2, pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, 90, 0])
        cylinder(d = m25_hole, h = standoff_pi + 3, $fn = 20);
}

module shell_bosses() {
    for (y = boss_y) translate([W - wall - fit - boss[0], y - boss[1] / 2, wall - 0.01]) cube(boss + [0, 0, 0.01]);
}

module insert_holes() {
    for (h = conv_holes) translate(conv_insert_pos(h) + [0.01, 0, 0]) rotate([0, -90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    for (y = div_top_y) translate([div_cx(), y, H - wall - insert_h + 0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    for (y = boss_y) translate([W - wall - fit + 0.01, y, wall + boss[2] / 2]) rotate([0, -90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
}

module mount_ears() {
    for (x = ear_x) for (s = [-1, 1]) translate([x, s < 0 ? -ear[1] : D, 0]) difference() {
        hull() {
            translate([-ear[0] / 2, s < 0 ? ear[1] - 1 : 0, 0]) cube([ear[0], 1, wall]);
            translate([0, ear[1] / 2, 0]) cylinder(d = ear[0], h = wall, $fn = 40);
        }
        translate([0, ear[1] / 2, -0.01]) cylinder(d = mount_d, h = wall + 1, $fn = 24);
    }
}

module back_cuts() {
    yb = D - wall;
    minkowski() { pi_ports(10); cube(2 * port_margin, center = true); }
    n = usb_notch_c;                                                     // the Pico's micro-USB goes out here
    translate([n[0], yb - 1, n[1]]) rotate([-90, 0, 0]) hull() for (k = [-1, 1])
        translate([k * (usb_notch[0] - usb_notch[1]) / 2, 0, 0]) cylinder(d = usb_notch[1], h = wall + 2, $fn = 32);
    for (i = [0 : 4]) translate([50 + i * 4, yb - 1, 10]) cube([2, wall + 2, 45]);          // vent behind the converter
}

module wall_tab_holes() {           // the main face's bottom tabs, screws from below
    for (y = [8, 58]) translate([wall + 5, y, 0]) {
        translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2 + 0.01, $fn = 32);
        cylinder(d = m3_clear, h = wall + 1, $fn = 24);
    }
}

module base(ears = true) {
    difference() {
        union() {
            floor_plate();
            back_panel();
            divider();
            pi_standoffs();
            shell_bosses();
            if (ears) mount_ears();
        }
        back_cuts();
        insert_holes();
        pi_standoff_holes();
        wall_tab_holes();
    }
}
