// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The front panel, assembled position (outer face at y = 0). The Pico board hangs from its
// 4 columns (heat-set inserts at their tips), the OLED shows through a chamfered window, the
// logo is inlaid 0.6 mm in black and blue, 2 tabs at the bottom are screwed from under the floor.
include <params.scad>

col_d = 6.8;                       // the board leaves a 7 mm keep-out round its M3 holes
front_tab = [9, 10, 8];            // X x Y x Z, insert from below
function front_tabs_x() = [wall + 0.5 + front_tab[0] / 2, W - wall - 0.5 - front_tab[0] / 2];
function oled_win_center() = oled_view_center();
function oled_win_top() = oled_win_center()[1] + oled_win[1] / 2 + wall;   // outer edge of the chamfer

LOGO_H = 24.8;                     // logo SVG height for 80 mm width

module logo_2d(c) {
    if (c == "todo") union() { import("logo/logo_negro.svg"); import("logo/logo_azul.svg"); }
    else import(str("logo/logo_", c, ".svg"));
}

// "negro", "azul" or "todo" (both, joined in 2D first: two touching solids break CGAL)
module logo_svg(c) {
    translate([W / 2 - logo_w / 2, 0, logo_zc - LOGO_H / 2])
        translate([0, logo_depth, 0]) rotate([90, 0, 0])
            linear_extrude(logo_depth) logo_2d(c);
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
    c = oled_win_center();
    w = oled_win[0]; h = oled_win[1];
    translate([c[0], 0, c[1]]) hull() {
        translate([-w / 2, wall - 0.01, -h / 2]) cube([w, 0.02 + 0.5, h]);
        translate([-w / 2 - wall, -0.01, -h / 2 - wall]) cube([w + 2 * wall, 0.02, h + 2 * wall]);
    }
}

module front_tabs() {
    for (x = front_tabs_x()) translate([x - front_tab[0] / 2, wall, wall])
        difference() {
            cube(front_tab);
            translate([front_tab[0] / 2, front_tab[1] / 2 + 0.5, -0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
        }
}

module frontal() {
    difference() {
        union() {
            cube([W, wall, H]);
            pico_columns();
            front_tabs();
        }
        oled_window();
        logo_svg("todo");
    }
}

// print orientation: outer face on the bed
module print_front() { translate([0, H, 0]) rotate([90, 0, 0]) children(); }
