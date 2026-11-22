// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The shell: roof + right side, one piece that slides down onto the base between the main face and the back;
// the narrow front with the XT60 and the switch is part of the base (front.scad) and stays. 3 M3 through the roof (main face's top tab, divider x2), 2 through the
// right side (floor bosses). tapa(fan = true): the shell_fan version, a 30 mm fan over the Pi (see params). Vents: air in low (front and right side, by the Pi), out high (right side by the
// converter, roof).
include <params.scad>

slot_w = 2;  slot_pitch = 4.5;
roof_vent = [[8, W - 5], [24, 71.5]];            // x range, y range
right_vent_y = [24, 78];
right_bands = [[8, pi_z0() + pi_w - 2], [conv_p0()[2] + 2, H - 8]];      // by the Pi, by the converter
roof_screws = [[wall + 5, 75], [wall + 5, 20], [(div_x[0] + div_x[1]) / 2, 20], [(div_x[0] + div_x[1]) / 2, 75]];
side_screw_y = [15, 86];
function side_screw_z() = wall + 9.5 / 2;

module m3_flat(l = 15) {             // head at z = 0, shaft up
    translate([0, 0, -0.01]) cylinder(d1 = m3_head_d, d2 = m3_clear, h = (m3_head_d - m3_clear) / 2 + 0.01, $fn = 32);
    cylinder(d = m3_clear, h = l, $fn = 24);
}

// a Pi-side slot at y that would run into the fan's square (fan version only)
function under_fan(y) = let(c = fan_c(), h = fan_size / 2 + fan_band_keep) y + slot_w > c[0] - h && y < c[0] + h;

module tapa_vents(fan = false) {
    for (x = [roof_vent[0][0] : slot_pitch : roof_vent[0][1] - slot_w])
        translate([x, roof_vent[1][0], H - wall - 1]) cube([slot_w, roof_vent[1][1] - roof_vent[1][0], wall + 2]);
    for (i = [0 : len(right_bands) - 1]) for (y = [right_vent_y[0] : slot_pitch : right_vent_y[1] - slot_w])
        if (!(fan && i == 0 && under_fan(y)))
            translate([W - wall - 1, y, right_bands[i][0]]) cube([wall + 2, slot_w, right_bands[i][1] - right_bands[i][0]]);
}

// the fan's opening on the right side: the circle, its 4 screw holes, and the wire slot (upwards, towards the
// Pi's GPIO header). The fan goes inside or outside on the same holes; turn it so its wires meet the slot.
module fan_cut() {
    c = fan_c();
    translate([W - wall - 1, c[0], c[1]]) rotate([0, 90, 0]) {
        cylinder(d = fan_open_d, h = wall + 2, $fn = 96);
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * fan_pitch / 2, sy * fan_pitch / 2, 0]) cylinder(d = fan_hole_d, h = wall + 2, $fn = 24);
        translate([-fan_slot_out, -fan_slot_w / 2, 0]) cube([fan_slot_out, fan_slot_w, wall + 2]);   // rotated: -X here is +Z
    }
}

// the fan itself, for the checks: inside (against the wall, towards the Pi) or outside
module ghost_fan(outside = false) {
    c = fan_c();
    translate([outside ? W : W - wall - fan_t, c[0] - fan_size / 2, c[1] - fan_size / 2]) cube([fan_t, fan_size, fan_size]);
}

module tapa(fan = false) {
    y1 = D - wall - fit;
    difference() {
        union() {
            translate([wall + fit, 0, H - wall]) cube([W - wall - fit, y1, wall]);        // roof
            translate([W - wall, 0, wall]) cube([wall, y1, H - wall]);                    // right side
        }
        tapa_vents(fan);
        if (fan) fan_cut();
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
