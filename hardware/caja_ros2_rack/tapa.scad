// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The shell: roof + right side + narrow front, one piece that slides down onto the base between
// the main face and the back. 3 M3 through the roof (main face's top tab, divider x2), 2 through the
// right side (floor bosses). Vents: air in low (front and right side, by the Pi), out high (right side by the
// converter, roof).
include <params.scad>

slot_w = 2;  slot_pitch = 4.5;
roof_vent = [[10, W - 6], [28, 68]];              // x range, y range
right_vent_y = [24, 78];
right_bands = [[8, pi_z0() + pi_w - 2], [conv_p0()[2] + 2, H - 8]];      // by the Pi, by the converter
front_vent = [[48, W - 6], [pi_z0(), pi_z0() + pi_w - 2]];               // x range, z range: in front of the Pi
roof_screws = [[wall + 5, 75], [(div_x[0] + div_x[1]) / 2, 20], [(div_x[0] + div_x[1]) / 2, 75]];
side_screw_y = [15, 86];
function side_screw_z() = wall + 9.5 / 2;

module m3_flat(l = 15) {             // head at z = 0, shaft up
    translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2 + 0.01, $fn = 32);
    cylinder(d = m3_clear, h = l, $fn = 24);
}

module tapa_vents() {
    for (x = [roof_vent[0][0] : slot_pitch : roof_vent[0][1] - slot_w])
        translate([x, roof_vent[1][0], H - wall - 1]) cube([slot_w, roof_vent[1][1] - roof_vent[1][0], wall + 2]);
    for (b = right_bands) for (y = [right_vent_y[0] : slot_pitch : right_vent_y[1] - slot_w])
        translate([W - wall - 1, y, b[0]]) cube([wall + 2, slot_w, b[1] - b[0]]);
    for (x = [front_vent[0][0] : slot_pitch : front_vent[0][1] - slot_w])
        translate([x, -1, front_vent[1][0]]) cube([slot_w, wall + 2, front_vent[1][1] - front_vent[1][0]]);
}

module tapa() {
    y1 = D - wall - fit;
    difference() {
        union() {
            translate([wall + fit, 0, H - wall]) cube([W - wall - fit, y1, wall]);        // roof
            translate([W - wall, 0, wall]) cube([wall, y1, H - wall]);                    // right side
            translate([wall + fit, 0, wall]) cube([W - wall - fit, wall, H - wall]);      // narrow front
        }
        tapa_vents();
        for (p = roof_screws) translate([p[0], p[1], H]) rotate([180, 0, 0]) m3_flat();
        for (y = side_screw_y) translate([W, y, side_screw_z()]) rotate([0, -90, 0]) m3_flat();
    }
}

function count_slots(a, b) = floor((b - a - slot_w) / slot_pitch) + 1;
module echo_vents() {
    echo("top_mm2", count_slots(roof_vent[0][0], roof_vent[0][1]) * slot_w * (roof_vent[1][1] - roof_vent[1][0]));
    echo("right_mm2", count_slots(right_vent_y[0], right_vent_y[1]) * slot_w * ((right_bands[0][1] - right_bands[0][0]) + (right_bands[1][1] - right_bands[1][0])));
    echo("front_mm2", count_slots(front_vent[0][0], front_vent[0][1]) * slot_w * (front_vent[1][1] - front_vent[1][0]));
    cube(0.01);
}

// print orientation: roof on the bed
module print_tapa() { translate([0, D, H]) rotate([180, 0, 0]) children(); }
