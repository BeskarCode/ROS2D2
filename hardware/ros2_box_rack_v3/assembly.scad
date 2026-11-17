// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Scenes for the rack box's assembly guide: assembled, exploded and the 8 steps (images only).
//   openscad -o step3.png -D 'scene="step"' -D 'step=3' assembly.scad
include <params.scad>
include <ghosts.scad>
include <wall.scad>
include <base.scad>
include <shell.scad>
include <frame.scad>
include <fasteners.scad>
include <models.scad>
include <light_pipes.scad>

scene = "assembled";
step = 1;
leds = false;                    // true: the LED face with its lenses

WHITE = [0.96, 0.96, 0.94];  GREY = [0.80, 0.80, 0.82];  ROD = [1, 0.55, 0.1];

// which part of the box each piece of hardware travels with
function grp(f) =
    f[1] == 1 ? (f[2][1] >= D - 0.01 || f[3] == [0, 1, 0] || f[3] == [0, -1, 0] ? "base" : f[3] == [-1, 0, 0] && f[2][0] < div_x[0] ? "wall"
               : f[2][0] < div_x[0] && f[3] != [-1, 0, 0] ? "wall" : "base") :
    f[1] == 2 ? "conv" : f[1] == 3 ? "pi" : f[1] == 4 ? "xt60" : f[1] == 5 ? "pico" :
    f[1] == 6 ? "base_bottom" : f[1] == 7 ? "shell" : "ears";

module hw_group(g, e = 0) {
    for (f = fasteners()) if (grp(f) == g) {
        if (f[0] == "nut_m3") color("silver") translate(f[2] + f[3] * e) along(f[3]) hw_shape("nut_m3");
        else color(hw_colour(f[0])) hw(f, e);
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
        color([0.05, 0.13, 0.25]) logo_svg("navy", leds = leds);
        color([0.25, 0.45, 0.75]) logo_svg("blue", leds = leds);
        color([0.45, 0.47, 0.5]) logo_svg("grey", leds = leds);
    }
}

module pared_assembly(board = true, rod = true, e_board = 0, e_rod = 0, e_screw = 0) {
    color(WHITE) pared(leds = leds); logos();
    if (leds) color([1, 0.35, 0.25, 0.85]) lentes_montadas();
    hw_group("wall");
    if (rod) translate([e_rod, 0, 0]) color(ROD) pulsador();
    if (board) translate([e_board, 0, 0]) { model_pico_board(); hw_group("pico", e_screw); }
}

// the HDMI panel jack on the back (flange outside, body in)
module model_hdmi() hdmi_turned() {
    color(BLACK) {
        translate([hdmi_c[0] - hdmi_flange[0] / 2, D, hdmi_c[1] - hdmi_flange[1] / 2]) cube([hdmi_flange[0], hdmi_flange_t, hdmi_flange[1]]);
        translate([hdmi_c[0] - hdmi_body[0] / 2, D - wall - hdmi_depth + 3, hdmi_c[1] - hdmi_body[1] / 2]) cube([hdmi_body[0], hdmi_depth - 3 + wall, hdmi_body[1]]);
    }
    color(METAL) translate([hdmi_c[0] - 7, D + hdmi_flange_t - 3, hdmi_c[1] - 2.5]) cube([14, 3.01, 5]);
}

module base_assembly(conv = true, pi = true, power = true) {
    color(GREY) base(); hw_group("base");
    if (power) { model_xt60(); model_switch(); hw_group("xt60"); }
    if (conv) { model_conv(); hw_group("conv"); }
    if (pi) { model_pi(); color(GREY) marco("pi4"); model_hdmi(); hw_group("pi"); }
}

module tapa_part(alpha = 1) { color([0.55, 0.57, 0.62, alpha]) tapa(); }

// standing: an ear in each site by the floor, a blank in the others; e pulls them out along their screws
module ears_assembly(e = 0) for (s = ear_sites) at_ear(s) translate([0, 0, -e]) color(GREY) {
    if (s[1] == "vertical") _ear(); else _ear_plate();
}

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
    xt = [xt60_c[0], wall + xt60_depth - xt60_flange_t, xt60_c[1]];      // back of the XT60's body (on the front)
    sw = [sw_c[0], wall + sw_depth, sw_c[1]];                            // back of the switch
    tp = (div_x[0] + div_x[1]) / 2;                                      // through the divider
    // 24 V, all on the Pi's side by the front: XT60 + -> switch -> converter IN+ ; XT60 - -> IN-
    cable([xt + [3.2, 0, 0], xt + [6, 3, 14], sw + [4, 0, -8], sw + [4, 0, 0]], RED);
    cable([sw + [-4, 0, 0], sw + [-6, 3, -8], cw(0) + [0, -4, 0], cw(0)], RED);
    cable([xt + [-3.2, 0, 0], xt + [-4, 3, 10], cw(1) + [0, -4, 0], cw(1)], BLK);
    // 5 V: converter OUT -> down in front of the Pi -> its angled USB-C ; and -> top pass -> over the Pico board -> J1
    pc = [pi_xp() + 4, pi_y0() + 11.2, pi_z0() - 9];
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [0, -1, -6], [45 + 2 * k, 10, pi_z0() + pi_w], [45 + 2 * k, 10, pc[2]], pc + [2 * k, -5, 0], pc + [2 * k, 0, 0]], [YEL, BLK][k], 2.6);
    // ... and through the divider's top pass, behind the Pico board, round its bx = 0 edge to J1
    j1 = pico2world(0, 59) + [-5, 0.8, 0];
    zp = cw(2)[2] + 8;
    for (k = [0, 1]) cable([cw(2 + k), cw(2 + k) + [0, -2, 6 + 2 * k], [tp, 6 + k, zp + 2 * k], [19.5 + k, 8 + k, zp + 2 * k],
                            [19.5 + k, 91 - k, zp + 2 * k], [19.5 + k, 91 - k, j1[2] + 8], [j1[0], 91 - k, j1[2] + 4], j1 + [0, 0, -1.5 + 3 * k]], [YEL, BLK][k], 1.8);
    // HDMI: the Pi's micro-HDMI 0 -> under the Pi -> up beside the converter -> the panel jack on the back
    ph = [pi_xp() + 4, pi_y0() + pi_hdmi0, pi_z0() - 9];
    cable([ph, ph + [0, 0, -4], [57, ph[1], wall + 3], [57, 83.5, wall + 3], [57, 83.5, hdmi_c[1]], [hdmi_c[0], D - wall - hdmi_depth + 3, hdmi_c[1]]], BLK, 5);
    // the Pico's micro-USB: straight up from the Pico, bent under the roof, along to the back notch
    u = pico2world(40, 0) + [-usb_plug[2], 0, 0];
    zb = u[2] + pico_usb_clear - 8;
    cable([u, [u[0], u[1], zb], [usb_notch_c[0], u[1], zb], [usb_notch_c[0], D - 6, usb_notch_c[1]]], BLK, 3.5);
    // sensor cables: straight out of each Dupont, through the bays
    for (r = dupont_rows) let(c = pico2world((r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
        cable([[c[0] - dupont_top, c[1], c[2]], [-25, c[1], c[2]]], SENS, 2.5);
}

if (scene == "abierta") { base_assembly(); pared_assembly(); hw_group("base_bottom"); wiring(); }
else if (scene == "assembled") { base_assembly(); pared_assembly(); hw_group("base_bottom"); usb_cable(); wiring(); tapa_part(0.25); hw_group("shell"); ears_assembly(); }
else if (scene == "assembled_back") { base_assembly(); pared_assembly(); hw_group("base_bottom"); usb_cable(); wiring(); tapa_part(); hw_group("shell"); ears_assembly(); }
else if (scene == "exploded") {
    base_assembly(conv = false, pi = false);
    translate([45, 0, 0]) { model_conv(); hw_group("conv", 12); }
    translate([75, 0, 0]) { model_pi(); hw_group("pi", 12); }
    translate([0, 30, 0]) { color(GREY) marco("pi4"); model_hdmi(); }
    translate([-110, 0, 0]) pared_assembly(e_board = 45, e_rod = 16, e_screw = 12);
    hw_group("base_bottom", 14);
    translate([0, 0, 160]) { tapa_part(); hw_group("shell", 14); }
}
else if (scene == "step") {
    if (step == 1) {                                            // inserts
        color(GREY) base(); hw_group("base", 12);
        translate([-60, 0, 0]) { color(WHITE) pared(); hw_group("wall", 12); }
    }
    else if (step == 2) {                                       // converter onto the divider
        color(GREY) base(); hw_group("base");
        translate([35, 0, 0]) { model_conv(); hw_group("conv", 12); }
        arrow(conv_p0() + [95, conv[1] / 2, conv[2] / 2], conv_p0() + [60, conv[1] / 2, conv[2] / 2]);
    }
    else if (step == 3) {                                       // Pi onto the divider
        base_assembly(pi = false);
        translate([45, 0, 0]) model_pi();
        translate([0, 25, 0]) { color(GREY) marco("pi4"); model_hdmi(); }
        hw_group("pi", 12);
        arrow([pi_x_pcb() + 115, pi_y0() + 40, pi_z0() + 28], [pi_x_pcb() + 75, pi_y0() + 40, pi_z0() + 28]);
    }
    else if (step == 4) {                                       // XT60 + switch on the fixed front
        color(GREY) base(); hw_group("base");
        translate([0, 35, 0]) { model_xt60(); model_switch(); }
        for (f = fasteners()) if (f[1] == 4) color("silver") hw(f, 10);
        arrow([xt60_c[0], 75, xt60_c[1]], [xt60_c[0], 45, xt60_c[1]]);
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
        translate([0, 0, 80]) { tapa_part(); hw_group("shell", 14); }
        arrow([W / 2 + 15, D / 2, H + 150], [W / 2 + 15, D / 2, H + 90]);
    }
    else if (step == 8) {                                       // USB out the back, onto the R2
        base_assembly(); pared_assembly(); hw_group("base_bottom");
        tapa_part(0.35); hw_group("shell"); usb_cable(); wiring();
        ears_assembly(16); hw_group("ears", 16);
    }
}
