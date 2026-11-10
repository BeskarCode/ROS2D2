// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Look-alike models for the renders and the guide (the tests use ghosts.scad). Each board is drawn in
// its own frame - u along it, v up, w out of its component face - and placed with one matrix.
include <params.scad>

PCB_GREEN = [0.10, 0.45, 0.20];  PCB_DARK = [0.05, 0.30, 0.15];
GOLD = [0.85, 0.70, 0.25];  METAL = [0.78, 0.78, 0.80];  BLACK = [0.12, 0.12, 0.12];

module frame(o, U, V, Wv) { multmatrix([[U[0], V[0], Wv[0], o[0]], [U[1], V[1], Wv[1], o[1]], [U[2], V[2], Wv[2], o[2]], [0, 0, 0, 1]]) children(); }
module bx(p, s, c) { color(c) translate(p) cube(s); }

// --- Pico carrier board, local: u = bx, v = -by (0 at the top edge, negative downwards), w = out of the parts side
module pico_board_local() {
    function q(bx, by) = [bx, -by];
    module header(bx, by, n, h = 11.5) {
        for (i = [0 : n - 1]) {
            bx([bx + i * 2.54 - 1.27, -by - 1.27, 0], [2.54, 2.54, 2.5], BLACK);
            color(GOLD) translate([bx + i * 2.54, -by, 0]) cylinder(d = 0.64, h = h, $fn = 8);
        }
    }
    bx([0, -pico_h, -pcb_t], [pico_w, pico_h, pcb_t], PCB_GREEN);
    for (sx = [40 - 8.89, 40 + 8.89]) bx([sx - 1.27, -53, 0], [2.54, 51, 8.5], BLACK);
    bx([40 - 10.5, -53, 8.5], [21, 51, 1], PCB_DARK);
    bx([40 - 4, -7.5, 9.5], [8, 5.5, 3.2], METAL);
    bx([40 - 3.5, -32, 9.5], [7, 7, 1], BLACK);
    for (i = [0 : 4]) header(1.73, 12 + i * 10, 4);
    for (y = [12, 24, 39, 51]) header(55, y, 6);
    header(27.5, 69, 6);
    bx([oled_rect[0], -oled_rect[3], oled_thick - 1.2], [oled_rect[2] - oled_rect[0], oled_rect[3] - oled_rect[1], 1.2], [0.1, 0.25, 0.6]);
    bx([oled_view[0] - 12.5, -oled_view[1] - 6.5, oled_thick], [25, 13, 0.6], [0.02, 0.02, 0.05]);
    color([0.4, 0.8, 1]) translate([oled_view[0] - 9, -oled_view[1] - 1.5, oled_thick + 0.65]) linear_extrude(0.1)
        text("ROS2D2", size = 3.2, font = "Liberation Sans:style=Bold");
    bx([sw1[0] - 3, -sw1[1] - 3, 0], [6, 6, sw1_h - 1.5], BLACK);
    color("white") translate([sw1[0], -sw1[1], sw1_h - 1.5]) cylinder(d = 3.5, h = 1.5, $fn = 20);
    bx([0.5, -64, 0], [10, 10, 10], [0.2, 0.7, 0.3]);                       // J1
    bx([34, -67, 0], [6, 4.5, 4.5], [0.95, 0.95, 0.9]);                     // Qwiic
}
module model_pico_board() { frame(pico2world(0, 0), [0, -1, 0], [0, 0, 1], [-1, 0, 0]) pico_board_local(); }

// --- Pi 4, local: u along the long edge from its front edge, v up from its bottom (USB-C) edge, w out of its parts side
module pi_local() {
    bx([0, 0, -pcb_t], [pi_l, pi_w, pcb_t], PCB_GREEN);
    for (vc = [9, 27]) bx([pi_l + pi_port_out - 17.5, vc - 6.6, 0], [17.5, 13.2, 16], METAL);
    for (vc = [9, 27]) for (dv = [-3.3, 3.3]) bx([pi_l + pi_port_out - 0.2, vc + dv - 1.2, 2.5], [0.4, 2.4, 11], [0.1, 0.2, 0.7]);
    bx([pi_l + pi_port_out - 21, 45.75 - 8, 0], [21, 16, 13.5], METAL);
    bx([pi_l + pi_port_out + 0.01, 45.75 - 5, 3], [0.3, 10, 8], BLACK);
    bx([3.5 + 7.7 - 4.5, -1, 0], [9, 7.5, 3.2], METAL);                     // USB-C, bottom edge
    for (c = [26, 39.5]) bx([c - 3.5, -1, 0], [7, 7.5, 3], METAL);           // micro-HDMI
    bx([7, pi_w - 6, 0], [51, 5, 8.5], BLACK);                               // GPIO, top edge
    bx([25, 20, 0], [15, 15, 2.4], METAL);
    for (h = pi_holes) color(GOLD) translate([h[0], h[1], 0]) cylinder(d = 5, h = 10, $fn = 6);
    bx([17, 13, 10], [30, 30, 10], BLACK);
    color([0.3, 0.3, 0.3]) translate([32, 28, 20.05]) cylinder(d = 26, h = 0.5, $fn = 40);
}
module model_pi() { frame([pi_x_pcb() + pcb_t, pi_y0(), pi_z0()], [0, 1, 0], [0, 0, 1], [1, 0, 0]) pi_local(); }

// --- converter on edge: base plate on the divider, fins to +X, cable gland on its front face ----------
module model_conv() {
    p = conv_p0();
    color(METAL) difference() {
        union() {
            translate(p + [0, 0, 4.9]) cube([3, conv[1], conv[2] - 9.8]);                      // base plate
            for (h = conv_holes) translate(p + [0, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = 9, h = conv_ear_t, $fn = 24);
            translate(p + [0, 6, 10]) cube([16, conv[1] - 12, conv[2] - 20]);                   // body
            for (i = [0 : 4]) translate(p + [0, 0, 7 + i * 12]) cube([conv[0], conv[1], 2.5]);  // fins
        }
        for (h = conv_holes) translate(p + [-1, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = 4, h = 5, $fn = 16);
    }
    color(BLACK) translate(p + [3, -1, 26]) cube([14, 2, 10]);
    for (i = [0 : 3]) color([[0.8, 0.1, 0.1], BLACK, [0.95, 0.8, 0.1], BLACK][i])
        translate(p + [4.75 + i * 3.5, 0, 31]) rotate([90, 0, 0]) cylinder(d = 3, h = conv_wires - 1, $fn = 12);
}

// --- XT60E-F (turned 90 deg) and KCD1 on the main face ------------------------------------------------
module model_xt60() {
    c = xt60_c;
    color([0.95, 0.8, 0.1]) {
        translate([-xt60_flange_t, c[0] - xt60_flange[1] / 2, c[1] - xt60_flange[0] / 2]) cube([xt60_flange_t, xt60_flange[1], xt60_flange[0]]);
        translate([0, c[0] - 8, c[1] - 8.3 / 2]) cube([xt60_depth - xt60_flange_t, 16, 8.3]);
    }
    for (dy = [-3.2, 3.2]) color(GOLD) translate([-xt60_flange_t - 0.01, c[0] + dy, c[1]]) rotate([0, -90, 0]) cylinder(d = 3.5, h = 0.5, $fn = 16);
}
module model_switch() {
    c = sw_c;
    color(BLACK) {
        translate([-2, c[0] - 21 / 2, c[1] - 15 / 2]) cube([2, 21, 15]);
        translate([sw_panel_t, c[0] - sw_cut[0] / 2 + 0.2, c[1] - sw_cut[1] / 2 + 0.2]) cube([sw_depth, sw_cut[0] - 0.4, sw_cut[1] - 0.4]);
    }
    color([0.8, 0.1, 0.1]) translate([-5, c[0] - 8, c[1] - 5.5]) cube([3, 16, 11]);
}

module models_all() { model_pico_board(); model_pi(); model_conv(); model_xt60(); model_switch(); }
