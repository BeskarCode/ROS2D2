// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Blanks for the unused connectors (only looks): each one plugs onto its header's pins like a Dupont and closes
// its strip of the bay flush with the face. The wall is not changed. Strips end halfway to the next connector,
// so a bay with nothing plugged in closes whole and a used connector keeps its finger room.

function blank_bay(i) = blank_bays[i];
function row_c(i) = (dupont_rows[i][1] + dupont_rows[i][3]) / 2;          // the connector's centre (by)
function blank_lo(i) = i > 0 && blank_bay(i - 1) == blank_bay(i) ? (row_c(i - 1) + row_c(i)) / 2 : pico_bays[blank_bay(i)][2] - 1;
function blank_hi(i) = i < len(dupont_rows) - 1 && blank_bay(i + 1) == blank_bay(i) ? (row_c(i) + row_c(i + 1)) / 2
                                                                                  : pico_bays[blank_bay(i)][4] + 1;
function blank_stem_x1() = pico_x() - 2.5 - blank_air;                    // 0.3 short of the header's plastic

// the strip of the bay (2D, Y-Z of the face) this blank closes
module blank_2d(i) let(b = pico_bays[blank_bay(i)], a = pico2world(b[3] + 1, blank_hi(i)), c = pico2world(b[1] - 1, blank_lo(i)))
    offset(delta = -blank_fit) intersection() {
        bays_2d();
        translate([a[1], a[2]]) square([c[1] - a[1], c[2] - a[2]]);
    }

// the real pins: 0.64 square, 6 mm over the plastic
function row_pins(i) = let(r = dupont_rows[i], n = round((r[2] - r[0]) / 2.54)) [for (k = [0 : n - 1]) [r[0] + 1.27 + 2.54 * k, row_c(i)]];
module blank_pins(i) for (p = row_pins(i)) let(w = pico2world(p[0], p[1]))
    translate([pico_x() - 2.5 - 6, w[1] - 0.32, w[2] - 0.32]) cube([6 + 2.5, 0.64, 0.64]);

module blank(i) {
    r = dupont_rows[i];
    a = pico2world(r[2], r[3]);  c = pico2world(r[0], r[1]);
    edge = pico2world(0, max(blank_lo(i), pico_bays[blank_bay(i)][2]) + blank_fit);   // the plate's edge on -by
    difference() {
        union() {
            yz_to_face(0, wall) blank_2d(i);
            translate([wall - 0.01, a[1] + 0.1, a[2] + 0.1]) cube([blank_stem_x1() - wall + 0.01, c[1] - a[1] - 0.2, c[2] - a[2] - 0.2]);
        }
        for (p = row_pins(i)) let(w = pico2world(p[0], p[1]))
            translate([blank_stem_x1() - blank_pin_depth, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d = blank_pin_d, h = blank_pin_depth + 1, $fn = 16);
        for (p = row_pins(i)) let(w = pico2world(p[0], p[1]))      // lead-in at the stem's end
            translate([blank_stem_x1() - blank_pin_lead, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d1 = blank_pin_d, d2 = blank_pin_d + 2 * blank_pin_lead + 0.02, h = blank_pin_lead + 0.01, $fn = 16);
        // the nail notch: a 45 deg chamfer along that edge, outside
        translate([0, D / 2, edge[2]]) rotate([0, 45, 0]) cube([blank_notch * sqrt(2), D + 2, blank_notch * sqrt(2)], center = true);
    }
}

// print: outer face on the bed, stem up, centred on its strip
module print_blank(i) let(b = pico_bays[blank_bay(i)], m = pico2world((b[1] + b[3]) / 2, row_c(i)))
    rotate([0, -90, 0]) translate([0, -m[1], -m[2]]) blank(i);

module blanks_all() for (i = [0 : len(dupont_rows) - 1]) translate([(i % 5) * 20, floor(i / 5) * 30, 0]) print_blank(i);
