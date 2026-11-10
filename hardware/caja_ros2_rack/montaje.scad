// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Scenes for the rack box's assembly guide: assembled, exploded and the 8 steps (images only).
//   openscad -o paso3.png -D 'scene="paso"' -D 'step=3' montaje.scad
include <params.scad>
include <ghosts.scad>
include <pared.scad>
include <base.scad>
include <tapa.scad>
include <fasteners.scad>
include <models.scad>

scene = "montada";
step = 1;

WHITE = [0.96, 0.96, 0.94];  GREY = [0.80, 0.80, 0.82];  ROD = [1, 0.55, 0.1];

// which part of the box each piece of hardware travels with
function grp(f) =
    f[1] == 1 ? (f[3] == [-1, 0, 0] && f[2][0] < div_x[0] ? "pared"
               : f[2][0] < div_x[0] && f[3] != [-1, 0, 0] ? "pared" : "base") :
    f[1] == 2 ? "conv" : f[1] == 3 ? "pi" : f[1] == 4 ? "xt60" : f[1] == 5 ? "pico" :
    f[1] == 6 ? "base_bottom" : f[1] == 7 ? "tapa" : "ears";

module hw_group(g, e = 0) {
    for (f = fasteners()) if (grp(f) == g) {
        if (f[0] == "nut_m3") color("silver") translate(f[2] + f[3] * e) along(f[3]) hw_shape("nut_m3");
        else color(f[0] == "ins_m3" ? "goldenrod" : "silver") hw(f, e);
    }
}

module arrow(from, to) {
    v = to - from; l = norm(v);
    color("red") translate(from) rotate([0, acos(v[2] / l), atan2(v[1], v[0])]) {
        cylinder(d = 1, h = l - 6, $fn = 8);
        translate([0, 0, l - 6]) cylinder(d1 = 4, d2 = 0, h = 6, $fn = 16);
    }
}

module logos() {
    translate([-0.03, 0, 0]) {
        color([0.05, 0.13, 0.25]) logo_svg("marino");
        color([0.25, 0.45, 0.75]) logo_svg("azul");
        color([0.45, 0.47, 0.5]) logo_svg("gris");
    }
}

module pared_assembly(board = true, rod = true, front = true, e_board = 0, e_rod = 0, e_screw = 0) {
    color(WHITE) pared(); logos();
    hw_group("pared");
    if (front) { model_xt60(); model_switch(); hw_group("xt60"); }
    if (rod) translate([e_rod, 0, 0]) color(ROD) pulsador();
    if (board) translate([e_board, 0, 0]) { model_pico_board(); hw_group("pico", e_screw); }
}

module base_assembly(conv = true, pi = true) {
    color(GREY) base(); hw_group("base");
    if (conv) { model_conv(); hw_group("conv"); }
    if (pi) { model_pi(); hw_group("pi"); }
}

module tapa_part(alpha = 1) { color([0.55, 0.57, 0.62, alpha]) tapa(); }

// the Pico's micro-USB out of the notch in the back, into a Pi USB port
module usb_cable() {
    n = [usb_notch_c[0], D, usb_notch_c[1]];
    u = [pi_x_pcb() + pcb_t + 8, D, pi_z0() + 27];
    pts = [n - [0, 6, 0], n + [0, 8, 0], n + [12, 16, -6], u + [-6, 16, 4], u + [0, 12, 0], u + [0, 2, 0]];
    color([0.1, 0.1, 0.1]) for (i = [0 : len(pts) - 2]) hull() { translate(pts[i]) sphere(d = 3.5, $fn = 12); translate(pts[i + 1]) sphere(d = 3.5, $fn = 12); }
    color(METAL) translate(u + [-6, 0, -2.5]) cube([12, 14, 5]);
}

// --- the wiring, for the pictures -------------------------------------------------------------
RED = [0.85, 0.1, 0.1];  BLK = [0.1, 0.1, 0.1];  YEL = [0.95, 0.8, 0.1];  SENS = [0.55, 0.55, 0.58];
module cable(pts, c, d = 2.2) {
    color(c) for (i = [0 : len(pts) - 2]) hull() { translate(pts[i]) sphere(d = d, $fn = 10); translate(pts[i + 1]) sphere(d = d, $fn = 10); }
}
module wiring() {
    p = conv_p0();
    cw = function(i) p + [4.75 + i * 3.5, -conv_wires + 1, 31];          // ends of the converter's 4 leads (in+, in-, out+, out-)
    xt = [wall + xt60_depth - xt60_flange_t, xt60_c[0], xt60_c[1]];      // back of the XT60's body
    sw = [wall + sw_depth, sw_c[0], sw_c[1]];                            // back of the switch
    pass = [(div_x[0] + div_x[1]) / 2, (div_pass[0] + div_pass[1]) / 2, wall + 5];
    // 24 V: XT60 + -> switch -> through the divider's gap -> converter IN+ ; XT60 - -> converter IN-
    cable([xt + [0, 3.2, 0], xt + [6, 15, -2], sw + [0, -4, -2]], RED);
    cable([sw + [0, 4, 0], sw + [8, -4, -4], pass + [0, -3, 0], [50, 40, wall + 4], [cw(0)[0], 16, 12], cw(0)], RED);
    cable([xt + [0, -3.2, 0], xt + [8, 6, -3], pass + [0, -7, -1], [54, 38, wall + 3], [cw(1)[0], 14, 14], cw(1)], BLK);
    // 5 V: converter OUT -> the Pi's USB-C (hanging under its bottom edge) and -> terminal J1
    pc = [pi_x_pcb() + pcb_t + 4, pi_y0() + 11.2, pi_z0() - 12];
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [0, -4, 6], [60 + 2 * k, 10, 50], pc + [6, 0, 0], pc], [YEL, BLK][k], 2.6);
    j1 = pico2world(0, 59) + [-5, 0.8, 0];
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [0, -3, -14], [58, 30, wall + 4], pass + [0, 4 + 2 * k, 0],
                            [26 + 2 * k, 86, wall + 6], [26 + 2 * k, 89, 40], j1 + [0, 0, -1.5 + 3 * k]], [YEL, BLK][k], 1.8);
    // the Pico's micro-USB: out to the side, towards the back notch
    u = pico2world(40, 0) + [-11, 0, 6];
    cable([u, u + [0, 10, 0], [u[0], D - 12, usb_notch_c[1]], [usb_notch_c[0], D - 6, usb_notch_c[1]]], BLK, 3.5);
    // sensor cables: two bundles up from the headers to the slot in the main face and out
    s = sensor_slot_c;
    cable([pico2world(6, 30) - [26, 0, 0], [6, 82, 80], [5, s[0] + 18, s[1]], [-25, s[0] + 18, s[1] + 4]], SENS, 6);
    cable([pico2world(66, 30) - [26, 0, 0], [6, 22, 80], [5, s[0] - 18, s[1]], [-25, s[0] - 18, s[1] + 4]], SENS, 6);
}

if (scene == "abierta") { base_assembly(); pared_assembly(); hw_group("base_bottom"); wiring(); }
else if (scene == "montada") { base_assembly(); pared_assembly(); hw_group("base_bottom"); usb_cable(); wiring(); tapa_part(0.25); hw_group("tapa"); }
else if (scene == "montada_atras") { base_assembly(); pared_assembly(); hw_group("base_bottom"); usb_cable(); wiring(); tapa_part(); hw_group("tapa"); }
else if (scene == "despiece") {
    base_assembly(conv = false, pi = false);
    translate([45, 0, 0]) { model_conv(); hw_group("conv", 12); }
    translate([75, 0, 0]) { model_pi(); hw_group("pi", 12); }
    translate([-110, 0, 0]) pared_assembly(e_board = 45, e_rod = 16, e_screw = 12);
    hw_group("base_bottom", 14);
    translate([0, 0, 160]) { tapa_part(); hw_group("tapa", 14); }
}
else if (scene == "paso") {
    if (step == 1) {                                            // inserts
        color(GREY) base(); hw_group("base", 12);
        translate([-60, 0, 0]) { color(WHITE) pared(); hw_group("pared", 12); }
    }
    else if (step == 2) {                                       // converter onto the divider
        color(GREY) base(); hw_group("base");
        translate([35, 0, 0]) { model_conv(); hw_group("conv", 12); }
        arrow(conv_p0() + [95, conv[1] / 2, conv[2] / 2], conv_p0() + [60, conv[1] / 2, conv[2] / 2]);
    }
    else if (step == 3) {                                       // Pi onto the divider
        base_assembly(pi = false);
        translate([45, 0, 0]) { model_pi(); hw_group("pi", 12); }
        arrow([pi_x_pcb() + 115, pi_y0() + 40, pi_z0() + 28], [pi_x_pcb() + 75, pi_y0() + 40, pi_z0() + 28]);
    }
    else if (step == 4) {                                       // XT60 + switch on the main face (from outside)
        color(WHITE) pared(); logos(); hw_group("pared");
        translate([-35, 0, 0]) { model_xt60(); model_switch(); }
        for (f = fasteners()) if (f[0] == "m3x10_flat") color("silver") translate([-35, 0, 0]) hw(f, 10);
        for (f = fasteners()) if (f[0] == "nut_m3") color("silver") translate(f[2] + f[3] * 10) along(f[3]) hw_shape("nut_m3");
    }
    else if (step == 5) {                                       // rod + Pico board onto the main face
        pared_assembly(e_board = 45, e_rod = 16, e_screw = 12);
        arrow([pico_x() + 95, 50, 60], [pico_x() + 52, 50, 60]);
    }
    else if (step == 6) {                                       // main face onto the base
        base_assembly();
        translate([-45, 0, 0]) pared_assembly();
        hw_group("base_bottom", 14);
        arrow([-80, D / 2, 60], [-50, D / 2, 60]);
    }
    else if (step == 7) {                                       // shell
        base_assembly(); pared_assembly(); hw_group("base_bottom");
        translate([0, 0, 80]) { tapa_part(); hw_group("tapa", 14); }
        arrow([W / 2 + 15, D / 2, H + 150], [W / 2 + 15, D / 2, H + 90]);
    }
    else if (step == 8) {                                       // USB out the back, onto the R2
        base_assembly(); pared_assembly(); hw_group("base_bottom");
        tapa_part(0.35); hw_group("tapa"); usb_cable(); wiring();
        hw_group("ears", 16);
    }
}
