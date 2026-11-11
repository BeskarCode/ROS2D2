// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The base: floor + back + the central divider (the Pi low on standoffs with M2.5 inserts, the converter high
// on M3 inserts) + floor bosses for the shell + ears for the R2. The main face screws to it from under the floor.
// The back has one window for the Pi's jacks, closed by a swappable frame (marco.scad), and the HDMI panel jack.
include <params.scad>

port_margin = 0.5;
standoff_d = 6.5;
back_boss_d = 7.5;  back_boss_l = 7;             // inside the back, for the frame's and the HDMI jack's inserts
ear = [14, 12];                                   // along X x out from the box (Y)
ear_x = [20, 60];
boss = [8, 10, 9.5];
boss_y = [15, 86];
div_top_y = [20, 75];
function div_cx() = (div_x[0] + div_x[1]) / 2;
function conv_insert_pos(h) = [div_x[1], conv_y + h[0], conv_p0()[2] + h[1]];
function hdmi_screws() = [for (s = [-1, 1]) [hdmi_c[0] + s * hdmi_pitch / 2, hdmi_c[1]]];   // (X, Z)

module floor_plate() { translate([wall + fit, 0, 0]) cube([W - wall - fit, D, wall]); }
module back_panel() { translate([wall + fit, D - wall, 0]) cube([W - wall - fit, wall, H]); }

module divider() {
    difference() {
        translate([div_x[0], wall + fit, wall - 0.01]) cube([div_x[1] - div_x[0], D - 2 * wall - fit + 0.02, H - 2 * wall + 0.01]);   // top flush with the roof's underside
        translate([div_x[0] - 1, div_pass[0], wall - 0.1]) cube([div_x[1] - div_x[0] + 2, div_pass[1] - div_pass[0], div_pass[2]]);
        p = div_pass_top; z0 = conv_p0()[2];
        translate([div_x[0] - 1, p[0], z0 + p[2]]) cube([div_x[1] - div_x[0] + 2, p[1] - p[0], p[3] - p[2]]);
    }
}

module pi_standoffs(extra = 0) {
    for (h = pi_holes) translate([div_x[1] - 0.01, pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, 90, 0])
        cylinder(d = standoff_d, h = standoff_pi - 0.05 + extra + 0.01, $fn = 32);
}
module pi_standoff_holes() {             // M2.5 inserts, mouth at the standoff's top
    for (h = pi_holes) translate([pi_x_pcb() + 0.01, pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, -90, 0])
        cylinder(d = ins25_d, h = ins25_h, $fn = 24);
}

module back_bosses() {
    for (p = concat(marco_screws(), hdmi_screws())) translate([p[0], D - wall + 0.01, p[1]]) rotate([90, 0, 0])
        intersection() {
            cylinder(d = back_boss_d, h = back_boss_l, $fn = 32);
            translate([wall + fit - p[0], -50, 0]) cube([W - wall - 2 * fit, 100, back_boss_l]);   // not into the main face nor the shell
        }
}

module shell_bosses() {
    for (y = boss_y) translate([W - wall - fit - boss[0], y - boss[1] / 2, wall - 0.01]) cube(boss + [0, 0, 0.01]);
}

module insert_holes() {
    for (h = conv_holes) translate(conv_insert_pos(h) + [0.01, 0, 0]) rotate([0, -90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    for (y = div_top_y) translate([div_cx(), y, H - wall - insert_h + 0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    for (y = boss_y) translate([W - wall - fit + 0.01, y, wall + boss[2] / 2]) rotate([0, -90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    for (p = concat(marco_screws(), hdmi_screws())) translate([p[0], D + 0.01, p[1]]) rotate([90, 0, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
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
    w = marco_win();                                                     // the frame's window
    translate([w[0], yb - 1, w[1]]) cube([w[2] - w[0], wall + 2, w[3] - w[1]]);
    translate([hdmi_c[0] - hdmi_body[0] / 2 - 0.3, yb - 1, hdmi_c[1] - hdmi_body[1] / 2 - 0.3])   // HDMI panel jack
        cube([hdmi_body[0] + 0.6, wall + 2, hdmi_body[1] + 0.6]);
    n = usb_notch_c;                                                     // the Pico's micro-USB goes out here
    translate([n[0], yb - 1, n[1]]) rotate([-90, 0, 0]) hull() for (k = [-1, 1])
        translate([k * (usb_notch[0] - usb_notch[1]) / 2, 0, 0]) cylinder(d = usb_notch[1], h = wall + 2, $fn = 32);
    for (i = [0 : 4]) translate([50 + i * 4, yb - 1, marco_screws()[1][1] + 6]) cube([2, wall + 2, H - wall - 6 - marco_screws()[1][1] - 6]);   // vent behind the converter
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
            back_bosses();
            shell_bosses();
            if (ears) mount_ears();
        }
        back_cuts();
        insert_holes();
        pi_standoff_holes();
        wall_tab_holes();
    }
}
