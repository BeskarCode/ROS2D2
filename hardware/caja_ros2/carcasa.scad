// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The U shell, assembled position: roof + left and right sides, between the front and the back
// panels. It slides down over the base, 4 M3 go through its sides into the floor bosses and
// 2 M3 through the roof into the top tabs of the front and the back. Vents: roof (most of it)
// and two bands on each side, low (air in) and high (air out).
include <params.scad>

roof_slot_x = [12, W - 12];
roof_slot_y = [16, D - 16];        // roof slots run along Y, clear of the roof screws
function roof_slots_x() = [for (x = [roof_slot_x[0] : slot_pitch : roof_slot_x[1] - slot_w]) x];

module carcasa_vents() {
    for (x = roof_slots_x()) translate([x, roof_slot_y[0], H - wall - 1]) cube([slot_w, roof_slot_y[1] - roof_slot_y[0], wall + 2]);
    for (b = [side_band_low, side_band_high]) for (y = side_slots_y()) for (x = [-1, W - wall - 1])
        translate([x, y, b[0]]) cube([wall + 2, slot_w, b[1] - b[0]]);
}

module carcasa_screws() {
    for (y = shell_screw_y()) {
        translate([0, y, shell_screw_z()]) rotate([0, 90, 0]) m3_flat_down();          // left, head outside
        translate([W, y, shell_screw_z()]) rotate([0, -90, 0]) m3_flat_down();         // right
    }
    for (y = top_tab_y()) translate([W / 2, y, H]) rotate([180, 0, 0]) m3_flat_down(); // roof
}

// countersunk M3 from z = 0 upwards (head at z = 0)
module m3_flat_down(l = 15) {
    translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2 + 0.01, $fn = 32);
    cylinder(d = m3_clear, h = l, $fn = 24);
}

module carcasa() {
    y0 = wall + fit; y1 = D - wall - fit;
    difference() {
        union() {
            translate([0, y0, wall]) cube([wall, y1 - y0, H - wall]);                // left
            translate([W - wall, y0, wall]) cube([wall, y1 - y0, H - wall]);         // right
            translate([0, y0, H - wall]) cube([W, y1 - y0, wall]);                   // roof
        }
        carcasa_vents();
        carcasa_screws();
    }
}

module echo_vents() {
    n_side = len(side_slots_y());
    side = n_side * slot_w * ((side_band_low[1] - side_band_low[0]) + (side_band_high[1] - side_band_high[0]));
    echo("top_mm2", len(roof_slots_x()) * slot_w * (roof_slot_y[1] - roof_slot_y[0]));
    echo("left_mm2", side); echo("right_mm2", side);
    cube(0.01);
}

// print orientation: roof on the bed
module print_shell() { translate([0, D, H]) rotate([180, 0, 0]) children(); }
