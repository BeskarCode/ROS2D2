// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Every insert, screw and nut of the rack box: [kind, step, position, direction] (position = where the
// head bears or the insert's mouth is; direction = where the shaft points). Draws the hardware in the
// guide, counts the BOM, and is checked against the printed parts (screws only through holes).
include <params.scad>

// kind -> [length, shaft d (for drawing/checks), head type, head d, head h]
function fkind(k) =
    k == "ins_m3"     ? [5.7, 3.9, "none", 0, 0] :
    k == "ins_m25"    ? [5, 3.5, "none", 0, 0] :
    k == "m3x8_flat"  ? [8, 2.9, "flat", 6.0, 1.4] :
    k == "m3x6_pan"   ? [6, 2.9, "pan", 5.5, 2.4] :
    k == "m3x6_cyl"   ? [6, 2.9, "cyl", 5.5, 3] :
    k == "m3x10_flat" ? [10, 2.9, "flat", 6.0, 1.4] :
    k == "nut_m3"     ? [2.4, 5.5, "nut", 0, 0] :
    k == "m25x6"      ? [6, 2.0, "pan", 4.5, 1.8] :
    k == "m4x12"      ? [12, 3.9, "pan", 7, 2.8] : undef;


function _ears() = [for (x = [20, 60]) for (y = [-6, D + 6]) [x, y]];
function _div_cx() = (div_x[0] + div_x[1]) / 2;
function _back_screws() = let(w = marco_win(), xc = (w[0] + w[2]) / 2) [[xc, w[1] - 6], [xc, w[3] + 5]];
function _hdmi_screws() = [for (s = [-1, 1]) [hdmi_c[0] + s * hdmi_pitch / 2, hdmi_c[1]]];

function fasteners() = concat(
    // step 1: inserts
    [for (h = pico_holes) ["ins_m3", 1, pico2world(h[0], h[1]) - [0.05, 0, 0], [-1, 0, 0]]],
    [for (y = [8, 58]) ["ins_m3", 1, [wall + 5, y, wall], [0, 0, 1]]],
    [["ins_m3", 1, [wall + 5, 75, H - wall], [0, 0, -1]]],
    [for (y = [20, 75]) ["ins_m3", 1, [_div_cx(), y, H - wall], [0, 0, -1]]],
    [for (y = [15, 86]) ["ins_m3", 1, [W - wall - fit, y, wall + 9.5 / 2], [-1, 0, 0]]],
    [for (h = conv_holes) ["ins_m3", 1, [div_x[1], conv_y + h[0], conv_p0()[2] + h[1]], [-1, 0, 0]]],
    [for (h = pi_holes) ["ins_m25", 1, [pi_x_pcb(), pi_y0() + h[0], pi_z0() + h[1]], [-1, 0, 0]]],
    [for (p = concat(_back_screws(), _hdmi_screws())) ["ins_m3", 1, [p[0], D, p[1]], [0, -1, 0]]],
    [for (s = [-1, 1]) ["ins_m3", 1, [0, xt60_c[0] + s * xt60_hole_pitch / 2, xt60_c[1]], [1, 0, 0]]],
    // step 2: converter onto the divider
    [for (h = conv_holes) ["m3x6_cyl", 2, [div_x[1] + conv_ear_t, conv_y + h[0], conv_p0()[2] + h[1]], [-1, 0, 0]]],
    // step 3: Pi onto the divider's standoffs, then the back frame for that Pi and the HDMI panel jack
    [for (h = pi_holes) ["m25x6", 3, [pi_x_pcb() + pcb_t, pi_y0() + h[0], pi_z0() + h[1]], [-1, 0, 0]]],
    [for (p = _back_screws()) ["m3x6_pan", 3, [p[0], D + marco_t, p[1]], [0, -1, 0]]],
    [for (p = _hdmi_screws()) ["m3x6_pan", 3, [p[0], D + hdmi_flange_t, p[1]], [0, -1, 0]]],
    // step 4: XT60E-F from outside the main face, into the inserts
    [for (s = [-1, 1]) ["m3x8_flat", 4, [-xt60_flange_t, xt60_c[0] + s * xt60_hole_pitch / 2, xt60_c[1]], [1, 0, 0]]],
    // step 5: Pico board onto the main face's columns
    [for (h = pico_holes) ["m3x6_pan", 5, pico2world(h[0], h[1]) + [pcb_t, 0, 0], [-1, 0, 0]]],
    // step 6: main face onto the base, from under the floor
    [for (y = [8, 58]) ["m3x8_flat", 6, [wall + 5, y, 0], [0, 0, 1]]],
    // step 7: shell
    [["m3x8_flat", 7, [wall + 5, 75, H], [0, 0, -1]]],
    [for (y = [20, 75]) ["m3x8_flat", 7, [_div_cx(), y, H], [0, 0, -1]]],
    [for (y = [15, 86]) ["m3x8_flat", 7, [W, y, wall + 9.5 / 2], [-1, 0, 0]]],
    // step 8: onto the R2
    [for (e = _ears()) ["m4x12", 8, [e[0], e[1], wall], [0, 0, -1]]]
);

function count_kind(k) = len([for (f = fasteners()) if (f[0] == k) 1]);

// is some screw's tip inside this insert?
function _tip(f) = f[2] + f[3] * fkind(f[0])[0];
function _is_insert(k) = k == "ins_m3" || k == "ins_m25";
function _in_insert(p, ins) = let(a = ins[2], d = ins[3], v = p - a, t = v * d, r = norm(v - d * t))
    t >= 0 && t <= fkind(ins[0])[0] + 0.5 && r < 0.5;
function inserts_without_screw() = len([for (i = fasteners()) if (_is_insert(i[0]))
    if (len([for (s = fasteners()) if (!_is_insert(s[0]) && _in_insert(_tip(s), i)) 1]) == 0) 1]);

// orient +Z along d (axis-aligned directions only)
module along(d) {
    if (d == [0, 0, 1]) children();
    else if (d == [0, 0, -1]) rotate([180, 0, 0]) children();
    else if (d == [1, 0, 0]) rotate([0, 90, 0]) children();
    else if (d == [-1, 0, 0]) rotate([0, -90, 0]) children();
    else if (d == [0, 1, 0]) rotate([-90, 0, 0]) children();
    else if (d == [0, -1, 0]) rotate([90, 0, 0]) children();
}

// one piece of hardware, its shaft along +Z from z = 0 (the bearing face)
module hw_shape(k) {
    s = fkind(k);
    if (s[2] == "none") cylinder(d = s[1], h = s[0], $fn = 24);                         // insert
    else if (s[2] == "nut") translate([0, 0, -s[0]]) cylinder(d = s[1] / cos(30), h = s[0], $fn = 6);
    else {
        cylinder(d = s[1], h = s[0], $fn = 20);
        if (s[2] == "flat") cylinder(d1 = s[3], d2 = s[1], h = s[4], $fn = 24);
        else translate([0, 0, -s[4]]) cylinder(d = s[3], h = s[4], $fn = 24);
    }
}

// explode = pull it back against its direction by that many mm (plus an arrow)
module hw(f, explode = 0, arrow = true) {
    translate(f[2] - f[3] * explode) along(f[3]) hw_shape(f[0]);
    if (explode > 0 && arrow)
        color("red") translate(f[2] - f[3] * (explode - 1)) along(f[3]) {
            cylinder(d = 0.6, h = explode - 4, $fn = 8);
            translate([0, 0, explode - 4]) cylinder(d1 = 2.2, d2 = 0, h = 3, $fn = 12);
        }
}

module hardware(kind = "all", step = 0, explode = 0) {
    for (f = fasteners())
        if ((kind == "all" || f[0] == kind) && (step == 0 || f[1] == step))
            color(_is_insert(f[0]) ? "goldenrod" : "silver") hw(f, explode);
}
