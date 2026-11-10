// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Scenes for the assembly guide (MONTAJE.md / ASSEMBLY.md): the box with its boards, the
// exploded view and the 8 steps. Images only; build_docs.py renders them.
//   openscad -o paso3.png -D 'scene="paso"' -D 'step=3' montaje.scad
include <params.scad>
include <ghosts.scad>
include <frontal.scad>
include <base.scad>
include <carcasa.scad>
include <fasteners.scad>
include <models.scad>

scene = "montada";
step = 1;

WHITE = [0.96, 0.96, 0.94];
GREY = [0.80, 0.80, 0.82];
ROD = [1, 0.55, 0.1];

// which part of the box each piece of hardware travels with
function grp(f) =
    f[1] == 1 ? (f[3] == [0, -1, 0] || f[3] == [0, 0, 1] ? "frontal"
                : (f[2][2] == H - wall ? (f[2][1] < D / 2 ? "frontal" : "base") : "base")) :
    f[1] == 2 ? "conv" : f[1] == 3 ? "xt60" : f[1] == 4 ? "pi" : f[1] == 5 ? "pico" :
    f[1] == 6 ? "base_bottom" : f[1] == 7 ? "carcasa" : "ears";

module hw_group(g, e = 0) {
    for (f = fasteners()) if (grp(f) == g) {
        if (f[0] == "nut_m3") color("silver") translate(f[2] + f[3] * e) along(f[3]) hw_shape("nut_m3");
        else color(f[0] == "ins_m3" ? "goldenrod" : "silver") hw(f, e);
    }
}

module arrow(from, to) {         // red arrow, for parts that move as a whole
    v = to - from; l = norm(v);
    color("red") translate(from) rotate([0, acos(v[2] / l), atan2(v[1], v[0])]) {
        cylinder(d = 1, h = l - 6, $fn = 8);
        translate([0, 0, l - 6]) cylinder(d1 = 4, d2 = 0, h = 6, $fn = 16);
    }
}

module front_assembly(board = true, rod = true, e_board = 0, e_rod = 0, e_screw = 0) {
    color(WHITE) frontal();
    translate([0, -0.03, 0]) {          // a hair proud of the face: no z-fighting in the preview
        color([0.05, 0.13, 0.25]) frontal_logo("marino");
        color([0.25, 0.45, 0.75]) frontal_logo("azul");
        color([0.45, 0.47, 0.5]) frontal_logo("gris");
    }
    hw_group("frontal");
    if (rod) translate([0, e_rod, 0]) color(ROD) pulsador();
    if (board) translate([0, e_board, 0]) { model_pico_board(); hw_group("pico", e_screw); }
}

module base_assembly(conv = true, back = true, pi = true) {
    color(GREY) base();
    hw_group("base");
    if (conv) { model_conv(); hw_group("conv"); }
    if (back) { model_xt60(); model_switch(); hw_group("xt60"); }
    if (pi) { model_pi(); hw_group("pi"); }
}

module shell(alpha = 1) { color([0.55, 0.57, 0.62, alpha]) carcasa(); }

// the Pico's micro-USB going out through the sensor slot into a Pi USB at the back
module usb_cable() {
    s = [sensor_slot_c[0] + 8, D, sensor_slot_c[1]];
    u = [pi_x_pcb() - 8, D, pi_z0() + 47 + 3.3];
    pts = [s - [0, 6, 0], s + [0, 8, 0], s + [10, 18, -8], u + [-10, 18, 6], u + [0, 14, 0], u + [0, 2, 0]];
    color([0.1, 0.1, 0.1]) for (i = [0 : len(pts) - 2]) hull() { translate(pts[i]) sphere(d = 3.5, $fn = 12); translate(pts[i + 1]) sphere(d = 3.5, $fn = 12); }
    color(METAL) translate(u + [-6, 0, -2.5]) cube([12, 14, 5]);
}

// --- the wiring, for the pictures -------------------------------------------------------------
RED = [0.85, 0.1, 0.1];  BLK = [0.1, 0.1, 0.1];  YEL = [0.95, 0.8, 0.1];  SENS = [0.55, 0.55, 0.58];
module cable(pts, c, d = 2.2) {
    color(c) for (i = [0 : len(pts) - 2]) hull() { translate(pts[i]) sphere(d = d, $fn = 10); translate(pts[i + 1]) sphere(d = d, $fn = 10); }
}
module wiring() {
    cw = function(i) [conv_pos[0] + conv_wire_x - 5.25 + i * 3.5, conv_pos[1] + conv[1] + conv_wires - 1, wall + conv_lift + 10];
    sw = [sw_c[0], D - sw_panel_t - sw_depth, sw_c[1]];
    xt = [xt60_c[0], D - xt60_depth + xt60_flange_t, xt60_c[1]];
    // 24 V: XT60 + -> switch -> converter IN+ ; XT60 - -> converter IN-
    cable([cw(0), cw(0) + [-6, 0, -1], sw + [4, 0, 0]], RED);
    cable([sw + [-4, 0, 0], sw + [-12, 2, 5], xt + [0, 0, 3.2]], RED);
    cable([cw(1), cw(1) + [-14, -4, -8], [22, D - 21, 12], xt + [0, 0, -3.2]], BLK);
    // 5 V: converter OUT -> USB-C of the Pi (its plug on the top edge) and -> terminal J1
    pc = [pi_x_pcb() - 4, pi_y0() + 11.2, pi_z0() + pi_w + 10];
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [10, -2, 8], [72 + 2 * k, 95, 96], [86, 62, 101], pc + [0, 0, 2]], [YEL, BLK][k], 2.6);
    j1 = pico2world(0, 59) + [0.5, -5, 0];
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [-12, -8, -8], [9 + 2 * k, 75, 9], [8 + 2 * k, 30, 26], j1 + [0, 0, -1.5 + 3 * k]], [YEL, BLK][k], 1.8);
    // the Pico's micro-USB: out to the left, along the top to the back slot
    u = pico2world(40, 0) + [0, -11, 6];
    cable([u, u + [-12, 0, 0], [10, u[1], u[2]], [9, 45, 101], [12, D - 12, 100], [sensor_slot_c[0] + 8, D - 6, sensor_slot_c[1]]], BLK, 3.5);
    // sensor cables: left bundle (US1-5) and right bundle (VL1-4) to the back slot and out
    cable([pico2world(6, 30) - [0, 26, 0], [6, 14, 72], [6, 60, 98], [14, D - 10, 100], [16, D + 25, 100]], SENS, 6);
    cable([pico2world(66, 30) - [0, 26, 0], [99, 14, 72], [99, 60, 93], [98, D - 10, 93], [36, D - 6, 100], [36, D + 25, 100]], SENS, 6);
}

if (scene == "abierta") {
    base_assembly(); front_assembly(); hw_group("base_bottom"); wiring();
}
else if (scene == "montada") {
    base_assembly(); front_assembly(); hw_group("base_bottom"); usb_cable(); wiring();
    shell(0.25); hw_group("carcasa");
}
else if (scene == "montada_atras") {
    base_assembly(); front_assembly(); hw_group("base_bottom"); usb_cable(); wiring();
    shell(); hw_group("carcasa");
}
else if (scene == "despiece") {
    base_assembly(conv = false, back = false, pi = false);
    translate([0, 0, 40]) { model_conv(); hw_group("conv", 14); }
    translate([0, 40, 0]) { model_xt60(); model_switch(); hw_group("xt60", 12); }
    translate([-95, 0, 25]) { model_pi(); hw_group("pi", 14); }
    translate([0, -120, 0]) front_assembly(e_board = 50, e_rod = 18, e_screw = 14);
    hw_group("base_bottom", 16);
    translate([0, 0, 165]) { shell(); hw_group("carcasa", 16); }
}
else if (scene == "paso") {
    if (step == 1) {                                           // inserts
        color(GREY) base(); hw_group("base", 12);
        // the front turned round, inside towards the viewer
        translate([W, -45, 0]) rotate([0, 0, 180]) { color(WHITE) frontal(); hw_group("frontal", 12); }
    }
    else if (step == 2) {                                      // converter
        color(GREY) base(); hw_group("base");
        translate([0, 0, 35]) { model_conv(); hw_group("conv", 14); }
        arrow([conv_pos[0] + conv[0] / 2, conv_pos[1] - 8, 65], [conv_pos[0] + conv[0] / 2, conv_pos[1] - 8, 35]);
    }
    else if (step == 3) {                                      // XT60 + switch, from the back
        base_assembly(back = false, pi = false);
        translate([0, 35, 0]) { model_xt60(); model_switch(); }
        for (f = fasteners()) if (f[0] == "m3x10_flat") color("silver") translate([0, 35, 0]) hw(f, 12);
        for (f = fasteners()) if (f[0] == "nut_m3") color("silver") translate(f[2] + f[3] * 12) along(f[3]) hw_shape("nut_m3");
        arrow([sw_c[0], D + 60, sw_c[1]], [sw_c[0], D + 38, sw_c[1]]);
    }
    else if (step == 4) {                                      // Pi
        base_assembly(pi = false);
        translate([-45, 0, 0]) { model_pi(); hw_group("pi", 14); }
        arrow([pi_x_pcb() - 75, pi_y0() + 40, pi_z0() + 28], [pi_x_pcb() - 52, pi_y0() + 40, pi_z0() + 28]);
    }
    else if (step == 5) {                                      // rod + Pico board on the front
        front_assembly(e_board = 45, e_rod = 16, e_screw = 14);
        arrow([pico_x0() + 40, pico_y() + 95, 55], [pico_x0() + 40, pico_y() + 50, 55]);
    }
    else if (step == 6) {                                      // front onto the base
        base_assembly();
        translate([0, -45, 0]) front_assembly();
        hw_group("base_bottom", 14);
        arrow([W / 2, -70, 60], [W / 2, -48, 60]);
    }
    else if (step == 7) {                                      // shell
        base_assembly(); front_assembly(); hw_group("base_bottom");
        translate([0, 0, 75]) { shell(); hw_group("carcasa", 14); }
        arrow([W / 2, D / 2, H + 140], [W / 2, D / 2, H + 85]);
    }
    else if (step == 8) {                                      // USB out the back, onto the R2
        base_assembly(); front_assembly(); hw_group("base_bottom");
        shell(0.35); hw_group("carcasa"); usb_cable(); wiring();
        hw_group("ears", 16);
    }
}
