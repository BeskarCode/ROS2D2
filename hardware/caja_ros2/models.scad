// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Look-alike models of what goes in the box, for the renders and the assembly guide only (the
// tests use the plain ghosts in ghosts.scad). Assembled positions, same axes as params.scad.
include <params.scad>

PCB_GREEN = [0.10, 0.45, 0.20];
PCB_DARK = [0.05, 0.30, 0.15];
GOLD = [0.85, 0.70, 0.25];
METAL = [0.78, 0.78, 0.80];
BLACK = [0.12, 0.12, 0.12];

module bx(p0, s, c) { color(c) translate(p0) cube(s); }

// --- Pico carrier board: parts face -Y. b(bx, by, dz) = board point, dz mm in front of it -------
function b(bx, by, dz = 0) = pico2world(bx, by) - [0, dz, 0];

module pin_header(bx, by, n, h = 11.5) {          // pins along +bx
    for (i = [0 : n - 1]) {
        bx(b(bx + i * 2.54 - 1.27, by + 1.27, 2.5) - [0, 0, 0], [2.54, 2.5, 2.54], BLACK);
        color(GOLD) translate(b(bx + i * 2.54, by, h)) rotate([-90, 0, 0]) cylinder(d = 0.64, h = h, $fn = 8);
    }
}

module model_pico_board() {
    x0 = pico_x0(); y = pico_y(); zt = pico_ztop();
    bx([x0, y, zt - pico_h], [pico_w, pcb_t, pico_h], PCB_GREEN);
    // Pico 2 on its two socket strips (USB end at the top edge)
    for (sx = [40 - 8.89, 40 + 8.89]) bx(b(sx - 1.27, 2 + 51, 8.5), [2.54, 8.5, 51], BLACK);
    bx(b(40 - 10.5, 2 + 51, 8.5 + 1), [21, 1, 51], PCB_DARK);
    bx(b(40 - 4, 2 + 5.5, 8.5 + 1 + 3.2), [8, 3.2, 5.5], METAL);         // its micro-USB
    bx(b(40 - 3.5, 2 + 30, 8.5 + 1 + 1), [7, 1, 7], BLACK);               // RP2350
    // sensor headers
    for (i = [0 : 4]) pin_header(3 - 1.27 + 1.27, 12 + i * 10, 4);
    for (y = [12, 24, 39, 51]) pin_header(55, y, 6);
    pin_header(27.5, 69, 6);                                               // EXP
    // OLED module, flat on the board, screen up (towards the front)
    bx(b(oled_rect[0], oled_rect[3], oled_thick), [oled_rect[2] - oled_rect[0], 1.2, oled_rect[3] - oled_rect[1]], [0.1, 0.25, 0.6]);
    bx(b(oled_view[0] - 12.5, oled_view[1] + 6.5, oled_thick + 0.6), [25, 0.6, 13], [0.02, 0.02, 0.05]);
    color([0.4, 0.8, 1]) translate(b(oled_view[0] - 9, oled_view[1] + 1, oled_thick + 0.65)) rotate([90, 0, 0])
        linear_extrude(0.1) text("ROS2D2", size = 3.2, font = "Liberation Sans:style=Bold");
    // DISPLAY button, 5 V terminal J1, Qwiic J3, USB-C J5
    bx(b(sw1[0] - 3, sw1[1] + 3, sw1_h - 1.5), [6, sw1_h - 1.5, 6], BLACK);
    color("white") translate(b(sw1[0], sw1[1], sw1_h)) rotate([90, 0, 0]) cylinder(d = 3.5, h = 1.5, $fn = 20);
    bx(b(0.5, 59 + 5, 10), [10, 10, 10], [0.2, 0.7, 0.3]);
    bx(b(34, 64.5 + 2.5, 4.5), [6, 4.5, 4.5], [0.95, 0.95, 0.9]);
    bx(b(-0.6, 75 + 4.5, 3.2), [7.5, 3.2, 9], METAL);
}

// --- Raspberry Pi 4: standing on the bracket, parts towards -X -----------------------------
module model_pi() {
    xp = pi_x_pcb(); y0 = pi_y0(); z0 = pi_z0();
    function p(py, pz, h) = [xp - h, y0 + py, z0 + pz];       // point h mm above the board
    bx([xp, y0, z0], [pcb_t, pi_l, pi_w], PCB_GREEN);
    // USB x2 (stacked pairs) and Ethernet, at the back edge
    ye = y0 + pi_l + pi_port_out;
    for (zc = [47, 29]) bx([xp - 16, ye - 17.5, z0 + zc - 6.6], [16, 17.5, 13.2], METAL);
    for (zc = [47, 29]) for (dz = [-3.3, 3.3]) bx([xp - 13.5, ye - 0.2, z0 + zc + dz - 1.2], [11, 0.4, 2.4], [0.1, 0.2, 0.7]);
    bx([xp - 13.5, ye - 21, z0 + 10.25 - 8], [13.5, 21, 16], METAL);
    bx([xp - 11, ye + 0.01, z0 + 10.25 - 5], [8, 0.3, 10], BLACK);
    // USB-C and 2x micro-HDMI on the top edge
    bx(p(3.5 + 7.7 - 4.5, pi_w - 7.5, 3.2), [3.2, 9, 7.5 + 1.2], METAL);
    for (c = [26, 39.5]) bx(p(c - 3.5, pi_w - 7.5, 3), [3, 7, 7.5 + 1], METAL);
    // GPIO header along the bottom edge, CPU, fan on standoffs over it
    bx(p(7, 1, 8.5), [8.5, 51, 5], BLACK);
    bx(p(25, 20, 2.4), [2.4, 15, 15], METAL);
    for (h = pi_holes) color(GOLD) translate(p(h[0], h[1], 0)) rotate([0, -90, 0]) cylinder(d = 5, h = 10, $fn = 6);
    bx(p(17, 13, 20), [10, 30, 30], BLACK);
    color([0.3, 0.3, 0.3]) translate(p(32, 28, 20.1)) rotate([0, -90, 0]) cylinder(d = 26, h = 0.5, $fn = 40);
}

// --- converter: aluminium, fins along Y, ears with the holes, 4 wires out of the -X face ---------
module model_conv() {
    p = [conv_pos[0], conv_pos[1], wall + conv_lift];
    ear = (conv[0] - 53.9) / 2;                                                   // drawing: body 53.9 long
    color(METAL) difference() {
        union() {
            translate(p + [ear, 0, 0]) cube([conv[0] - 2 * ear, conv[1], 3]);    // base plate
            for (h = conv_holes) translate(p + [h[0], h[1], 0]) cylinder(d = 9, h = conv_ear_t, $fn = 24);   // ears
            translate(p + [ear + 6, 6, 0]) cube([conv[0] - 2 * ear - 12, conv[1] - 12, 16]);   // body
            for (i = [0 : 4]) translate(p + [ear + 2 + i * 12, 0, 0]) cube([2.5, conv[1], conv[2]]);   // fins
        }
        for (h = conv_holes) translate(p + [h[0], h[1], -1]) cylinder(d = 4, h = 5, $fn = 16);
    }
    color(BLACK) translate(p + [conv_wire_x - 7, conv[1] - 1, 6]) cube([14, 2, 8]);                // cable gland
    for (i = [0 : 3]) color([[0.8, 0.1, 0.1], BLACK, [0.95, 0.8, 0.1], BLACK][i])                 // in +/-, out +/-
        translate(p + [conv_wire_x - 5.25 + i * 3.5, conv[1], 10]) rotate([-90, 0, 0]) cylinder(d = 3, h = conv_wires - 1, $fn = 12);
}

// --- XT60E-F on the back, flange outside ---------------------------------------------------
module model_xt60() {
    c = xt60_c; yb = D;
    color([0.95, 0.8, 0.1]) {
        translate([c[0] - xt60_flange[0] / 2, yb, c[1] - xt60_flange[1] / 2]) cube([xt60_flange[0], xt60_flange_t, xt60_flange[1]]);
        translate([c[0] - 8.3 / 2, yb - xt60_depth + xt60_flange_t, c[1] - 8]) cube([8.3, xt60_depth - xt60_flange_t, 16]);
    }
    for (dz = [-3.2, 3.2]) color(GOLD) translate([c[0], yb + xt60_flange_t + 0.01, c[1] + dz]) rotate([90, 0, 0]) cylinder(d = 3.5, h = 6, $fn = 16);
}

// --- KCD1 rocker on the back -------------------------------------------------------------------
module model_switch() {
    c = sw_c;
    color(BLACK) {
        translate([c[0] - 21 / 2, D, c[1] - 15 / 2]) cube([21, 2, 15]);
        translate([c[0] - sw_cut[0] / 2 + 0.2, D - sw_panel_t - sw_depth, c[1] - sw_cut[1] / 2 + 0.2]) cube([sw_cut[0] - 0.4, sw_depth, sw_cut[1] - 0.4]);
    }
    color([0.8, 0.1, 0.1]) translate([c[0] - 8, D + 2, c[1] - 5.5]) rotate([0, 0, 0]) cube([16, 3, 11]);
}

module models_all() { model_pico_board(); model_pi(); model_conv(); model_xt60(); model_switch(); }
