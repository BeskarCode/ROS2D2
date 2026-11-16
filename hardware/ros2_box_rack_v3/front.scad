// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The narrow front (y = 0): the power side. Part of the base (it stays when the shell comes off), with the male
// XT60 and the KCD1 switch high on the Pi side, over the Pi, and the air inlet in front of the Pi.
include <params.scad>

// the cuts, written on the main face's frame (see on_front() in params.scad)
module switch_cut() {
    c = fm(sw_c);
    translate([-1, c[0] - sw_cut[0] / 2, c[1] - sw_cut[1] / 2]) cube([wall + 2, sw_cut[0], sw_cut[1]]);
    translate([sw_panel_t, c[0] - sw_cut[0] / 2 - 3, max(c[1] - sw_cut[1] / 2 - 3, -1)])
        cube([wall, sw_cut[0] + 6, sw_cut[1] + 6]);
}

// the male XT60's lip goes through, its flange stays inside: only the lip's opening and 2 M3 through holes
module xt60_cut() {
    c = fm(xt60_c); f = xt60_cut_fit;
    translate([-1, c[0] - xt60_lip[1] / 2 - f, c[1] - xt60_lip[0] / 2 - f]) cube([wall + 2, xt60_lip[1] + 2 * f, xt60_lip[0] + 2 * f]);
    for (s = [-1, 1]) translate([-1, c[0] + s * xt60_hole_pitch / 2, c[1]]) rotate([0, 90, 0]) cylinder(d = xt60_hole_d, h = wall + 2, $fn = 24);
}

module front_vents() {
    for (x = [front_vent[0][0] : 4.5 : front_vent[0][1] - 2])
        translate([x, -1, front_vent[1][0]]) cube([2, wall + 2, front_vent[1][1] - front_vent[1][0]]);
}

module front_panel() {
    difference() {
        translate([wall + fit, 0, 0]) cube([W - 2 * wall - 2 * fit, wall, H - wall - 0.1]);   // under the roof, inside the shell's side
        on_front() { switch_cut(); xt60_cut(); }
        front_vents();
    }
}
