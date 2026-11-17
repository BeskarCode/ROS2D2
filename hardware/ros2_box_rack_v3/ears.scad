// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Removable mounting ears. An L piece screwed flush into a pocket of the fixed front or of the back (2 countersunk
// M3 into inserts): 8 sites, 4 per face. Standing (vertical) uses the 4 sites by the floor's edge, their lugs
// on the floor's plane (z = 0); lying on the shell's side (horizontal) the 4 by the x = W edge, lugs on x = W.
// The unused sites take a blank (the plate alone). One ear fits every site.
//
// The ear in its own frame (a, b, n): a across the plate from its edge by the box's edge, b along that edge,
// n into the box (n = 0: the box's outer face). Plate a 0..ear_plate[0], b 0..ear_plate[1], n 0..ear_pocket_t;
// lug a -ear_e..ear_lug_t, n -ear_lug..0: it also covers the ear_e strip between the pocket and the box's
// edge, so its outer face lands on the mounting plane.
include <params.scad>

// --- the 8 sites: [face, mode, start along the edge] ---
ear_sites = [["front", "vertical", 14], ["front", "vertical", 40],
             ["front", "horizontal", 74.5], ["front", "horizontal", 92],      // the Pi fills the front below z 73.5 from y 7
             ["back", "vertical", 3.5], ["back", "vertical", 20.5],
             ["back", "horizontal", 76], ["back", "horizontal", 127.9]];   // between the HDMI's top insert and the roof

// (a, b, n) -> box
function ear_m(s) = let(f = s[0] == "front", v = s[1] == "vertical", b0 = s[2],
                        A = v ? [0, 0, 1] : [-1, 0, 0], B = v ? [1, 0, 0] : [0, 0, 1], N = f ? [0, 1, 0] : [0, -1, 0],
                        O = [v ? b0 : W - ear_e, f ? 0 : D, v ? ear_e : b0])
    [[A[0], B[0], N[0], O[0]], [A[1], B[1], N[1], O[1]], [A[2], B[2], N[2], O[2]], [0, 0, 0, 1]];
function ear_pt(s, p) = let(m = ear_m(s)) [for (i = [0 : 2]) m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3]];
function ear_screws() = [for (k = [-1, 1]) [ear_screw_a, ear_plate[1] / 2 + k * ear_screw_pitch / 2]];   // (a, b)
module at_ear(s) multmatrix(ear_m(s)) children();

// --- the pieces, in their own frame ---
module _ear_plate() {
    difference() {
        cube([ear_plate[0], ear_plate[1], ear_pocket_t]);
        for (p = ear_screws()) translate([p[0], p[1], 0]) {      // countersunk M3, the head flush with n = 0
            translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2 + 0.01, $fn = 32);
            translate([0, 0, -1]) cylinder(d = m3_clear, h = ear_pocket_t + 2, $fn = 24);
        }
    }
}
// the lug's profile (a, n), extruded along b; its root over the ear_e strip stays 0.01 off the box's face
module _ear() {
    _ear_plate();
    difference() {
        multmatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(ear_plate[1])
            polygon([[-ear_e, -ear_lug], [ear_lug_t, -ear_lug], [ear_lug_t, 0.01], [0, 0.01], [0, -0.01], [-ear_e, -0.01]]);
        translate([-ear_e - 1, ear_plate[1] / 2, -ear_lug_hole]) rotate([0, 90, 0]) cylinder(d = mount_d, h = ear_e + ear_lug_t + 2, $fn = 24);
    }
}
module ear_blank_local() _ear_plate();

// to print: the L's profile on the bed (every layer holds the whole L), the blank flat
module ear() rotate([90, 0, 0]) _ear();                   // b (along the edge) up
module ear_blank() ear_blank_local();

// --- in the box ---
module ears_mounted(sites = ear_sites) for (s = sites) at_ear(s) _ear();
module blanks_mounted(sites = ear_sites) for (s = sites) at_ear(s) _ear_plate();
module ear_pockets(grow = 0) for (s = ear_sites) at_ear(s)
    translate([-ear_fit - grow, -ear_fit - grow, -1]) cube([ear_plate[0] + 2 * (ear_fit + grow), ear_plate[1] + 2 * (ear_fit + grow), ear_pocket_t + 1.05]);   // 0.05 deeper
// the pads stop under the roof (the shell slides over them)
module ear_pads() intersection() {
    for (s = ear_sites) at_ear(s) for (p = ear_screws())
        translate([p[0], p[1], wall - 0.01]) cylinder(d = boss_d, h = ear_pad_n() - wall + 0.01, $fn = 32);
    translate([-1, -1, -1]) cube([W + 2, D + 2, H - wall - fit + 1]);
}
module ear_insert_holes() for (s = ear_sites) at_ear(s) for (p = ear_screws())
    translate([p[0], p[1], ear_pocket_t - 0.01]) cylinder(d = insert_d, h = insert_h + 0.01, $fn = 24);
function ear_pad_n() = ear_pocket_t + insert_h + 0.5;          // how far into the box a pad reaches (from the outer face)
