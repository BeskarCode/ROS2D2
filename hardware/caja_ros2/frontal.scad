// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The front panel, assembled position (outer face at y = 0). The Pico board hangs from its
// 4 columns (heat-set inserts at their tips), the OLED shows through a chamfered window, the
// logo is inlaid 0.6 mm in black and blue, 2 tabs at the bottom are screwed from under the floor.
include <params.scad>

col_d = 8;                         // 2 mm of wall round the insert; the ghost keeps 8.4 mm clear
front_tab = [9, 10, 8];            // X x Y x Z, insert from below
function front_tabs_x() = [wall + 0.5 + front_tab[0] / 2, W - wall - 0.5 - front_tab[0] / 2];
function sw1_world() = pico2world(sw1[0], sw1[1]);
// left edge of the window: just clear of the push rod's guide (no chamfer on that side)
function oled_win_x() = [sw1_world()[0] + guide_od / 2 + 0.9, oled_view_center()[0] + oled_win[0] / 2];
function oled_win_center() = [(oled_win_x()[0] + oled_win_x()[1]) / 2, oled_view_center()[1] + oled_win_dz];
function oled_win_top() = oled_win_center()[1] + oled_win[1] / 2 + wall;   // outer edge of the chamfer
function oled_win_inner() = [oled_win_x()[0], oled_win_center()[1] - oled_win[1] / 2,
                             oled_win_x()[1], oled_win_center()[1] + oled_win[1] / 2];

LOGO_H = 24.8;                     // logo SVG height for 80 mm width

module logo_2d(c) {
    if (c == "todo") union() { import("logo/logo_negro.svg"); import("logo/logo_azul.svg"); }
    else import(str("logo/logo_", c, ".svg"));
}

// "negro", "azul" or "todo" (both, joined in 2D first: two touching solids break CGAL)
module logo_svg(c, depth = logo_depth) {
    translate([W / 2 - logo_w / 2, 0, logo_zc - LOGO_H / 2])
        translate([0, depth, 0]) rotate([90, 0, 0])
            linear_extrude(depth) logo_2d(c);
}

module frontal_logo(c) { logo_svg(c); }

module pico_columns(extra = 0) {
    for (h = pico_holes) translate(pico2world(h[0], h[1]))
        difference() {
            // 0.05 mm short of the board: touching faces would read as a collision in the tests
            translate([0, -extra - 0.05, 0]) rotate([90, 0, 0]) cylinder(d = col_d, h = pico_gap - extra - 0.05, $fn = 40);
            translate([0, 0.01, 0]) rotate([90, 0, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
        }
}

module oled_window() {
    r = oled_win_inner();
    difference() {
        hull() {
            translate([r[0], wall - 0.01, r[1]]) cube([r[2] - r[0], 0.02, r[3] - r[1]]);
            translate([r[0], -0.01, r[1] - wall]) cube([r[2] - r[0] + wall, 0.02, r[3] - r[1] + 2 * wall]);
        }
        // the window's corner gives way round the column behind it
        for (p = pico_holes) translate(pico2world(p[0], p[1]) - [0, pico_y() + 1, 0])
            rotate([-90, 0, 0]) cylinder(d = col_d + 1, h = wall + 2, $fn = 40);
    }
}

// --- push rod for the DISPLAY button ---------------------------------------------------
function rod_end_y() = pico_y() - sw1_h - rod_gap;               // its inner end, at rest

module rod_guide() {
    p = sw1_world();
    translate([p[0], 0, p[2]]) rotate([-90, 0, 0]) difference() {
        translate([0, 0, wall - 0.01]) cylinder(d = guide_od, h = guide_len + 0.01, $fn = 40);
        translate([0, 0, -1]) cylinder(d = rod_bore, h = wall + guide_len + 2, $fn = 32);
    }
}

module rod_hole() {
    p = sw1_world();
    translate([p[0], -1, p[2]]) rotate([-90, 0, 0]) cylinder(d = rod_bore, h = wall + 2, $fn = 32);
}

// assembled, pushed in by press mm
module pulsador(press = 0) {
    p = sw1_world();
    y0 = -rod_proud + press; y1 = rod_end_y() + press; yf = wall + guide_len + press;
    translate([p[0], 0, p[2]]) rotate([-90, 0, 0]) {
        hull() {                                                      // rod, tip chamfered
            translate([0, 0, y0]) cylinder(d = rod_d - 1, h = 0.01, $fn = 32);
            translate([0, 0, y0 + 0.5]) cylinder(d = rod_d, h = y1 - y0 - 0.5, $fn = 32);
        }
        translate([0, 0, yf]) cylinder(d = rod_flange[0], h = rod_flange[1], $fn = 40);   // stop collar
        translate([0, 0, yf + rod_flange[1] - 0.01])                   // 45 deg under it: prints inner end down
            cylinder(d1 = rod_flange[0], d2 = rod_d, h = (rod_flange[0] - rod_d) / 2, $fn = 40);
    }
}

// print orientation: standing on its inner end
module print_rod() {
    p = sw1_world();
    translate([0, 0, rod_end_y()]) rotate([-90, 0, 0]) translate([-p[0], 0, -p[2]]) children();
}

module front_tabs() {
    for (x = front_tabs_x()) translate([x - front_tab[0] / 2, wall, wall])
        difference() {
            cube(front_tab);
            translate([front_tab[0] / 2, front_tab[1] / 2 + 0.5, -0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
        }
}

// depth = logo_depth: AMS front (the logo bodies fill it); logo_depth_mono: one colour, engraved
module frontal(depth = logo_depth) {
    difference() {
        union() {
            cube([W, wall, H]);
            pico_columns();
            front_tabs();
            top_tab(top_tab_y()[0]);
            rod_guide();
        }
        oled_window();
        rod_hole();
        logo_svg("todo", depth);
    }
}

// print orientation: outer face on the bed
module print_front() { translate([0, H, 0]) rotate([90, 0, 0]) children(); }
