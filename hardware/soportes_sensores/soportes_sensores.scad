// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Tilting mounts for the HC-SR04 and the VL53L0X (GY-VL53L0XV2): a flat base with 2 countersunk M3 holes
// and two ears, and a cradle holding the sensor that pivots between them. One M3 per side is the axle,
// into a heat-set insert in the cradle; Hirth teeth on the ear and the cradle lock the angle every 10 deg.
// Tilt -30..+90 deg: 0 = the sensor looks straight out of the base, +90 = along it (pins edge up).
//   openscad -o base_hc.stl -D 'part="base"' -D 'sensor="hc"' soportes_sensores.scad
// Axes: X along the axle, Y across, Z up from the base's bottom.

sensor = "hc";            // "hc" | "vl"
part = "montado";         // base | cuna | montado | check_sweep | check_mesh; pictures: foto | angulos | piezas
tilt = 0;

// --- sensors: board X x Y x t, holes (X, Y), front height, back clearance, insert hole d x depth ------
function S(k) = sensor == "hc"
    ? [[45, 20, 1.5], [[-20.5, -8.25], [20.5, 8.25]], 12, 3, [3.2, 4]]     // HC-SR04: M2 inserts
    : [[25, 10.6, 1.6], [[-10, 0], [10, 0]], 2.5, 3, [4.0, 5]];            // VL53L0X: holes 3.5 at 20 -> M3 inserts
board = S()[0]; holes = S()[1]; front = S()[2]; so_h = S()[3]; sins = S()[4];

// --- common ------------------------------------------------------------------------------------
tp = 3;                    // cradle plate
m = 1.5;                   // plate margin round the board
so_d = sensor == "hc" ? 5.5 : 7;     // standoffs
rc = 7;                    // cheek / ear radius round the axle
tc = 6;                    // cheek thickness (M3 insert 5.7)
ins3 = [4.0, 6];           // M3 insert hole
te = 4;                    // ear thickness
tb = 3;                    // base plate
n_teeth = 36;  t_ri = 2.6;  t_ro = rc - 0.5;  t_h = 0.8;   // Hirth: 10 deg
gap = t_h + 0.1;           // cheek face to ear face, teeth meshed
m3_clear = 3.4;  csk_d = 6.4;  base_hole_y = 9;

pw = board[0] + 2 * m;  ph = board[1] + 2 * m;
xc = pw / 2 + tc;                        // cheek outer face
xe = xc + gap;                           // ear inner face
zc = -tp + rc;                           // axle in cradle coords (plate top z = 0, bottom -tp)
top = so_h + board[2] + front;           // highest point of the sensor over the plate

// the axle height over the base's bottom: the cradle sweeps -30..+90 without touching the base
corners = [for (y = [-ph / 2, ph / 2], z = [-tp, top]) [y, z - zc]];
function zlow(t) = min([for (c = corners) c[0] * sin(t) + c[1] * cos(t)]);   // rotate([-t,0,0]) sends +Z to +Y
zp = tb + max(rc + 0.5, -min([for (t = [-30 : 5 : 90]) zlow(t)]) + 1);
base_l = max(2 * rc, 2 * base_hole_y + csk_d + 2);

// --- Hirth teeth on the +Z face of a ring, base at z = 0 -----------------------------------------
module hirth(phase = 0) {
    a = 360 / n_teeth;
    for (k = [0 : n_teeth - 1]) let(t0 = phase + k * a)
        hull() for (p = [[t_ri, t0 - a / 2, 0], [t_ri, t0 + a / 2, 0], [t_ro, t0 - a / 2, 0], [t_ro, t0 + a / 2, 0],
                         [t_ri, t0, t_h * t_ri / t_ro], [t_ro, t0, t_h]])
            translate([p[0] * cos(p[1]), p[0] * sin(p[1]), p[2]]) cube(0.01, center = true);
}

// --- cradle (in its own coords: plate top z = 0, axle at [0, 0, zc]) -------------------------------
module cuna() {
    difference() {
        union() {
            translate([-pw / 2, -ph / 2, -tp]) cube([pw, ph, tp]);
            for (h = holes) translate([h[0], h[1], -0.01]) cylinder(d = so_d, h = so_h + 0.01, $fn = 32);
            for (s = [-1, 1]) {
                hull() {                                                   // cheek, flat bottom to print
                    translate([s > 0 ? pw / 2 - 0.01 : -xc, 0, zc]) rotate([0, 90, 0]) cylinder(r = rc, h = tc + 0.01, $fn = 48);
                    translate([s > 0 ? pw / 2 - 0.01 : -xc, -rc, -tp]) cube([tc + 0.01, 2 * rc, 0.01]);
                }
                translate([s * xc, 0, zc]) rotate([0, s * 90, 0]) hirth();
            }
        }
        for (h = holes) translate([h[0], h[1], so_h - sins[1]]) cylinder(d = sins[0], h = sins[1] + 1, $fn = 24);
        // window for the parts and pins on the board's back
        translate([0, 0, -tp - 1]) linear_extrude(tp + 2) offset(r = 2) offset(delta = -2)
            square([board[0] - 2 * (so_d + 1) - (sensor == "hc" ? 0 : -4), board[1] - (sensor == "hc" ? 6 : 1)], center = true);
        for (s = [-1, 1]) translate([s * (xc + t_h + 1), 0, zc]) rotate([0, -s * 90, 0]) cylinder(d = ins3[0], h = ins3[1] + t_h + 1, $fn = 24);
    }
}

// --- base -------------------------------------------------------------------------------------
module base() {
    difference() {
        union() {
            translate([-xe - te, -base_l / 2, 0]) cube([2 * (xe + te), base_l, tb]);
            for (s = [-1, 1]) {
                hull() {
                    translate([s > 0 ? xe : -xe - te, 0, zp]) rotate([0, 90, 0]) cylinder(r = rc, h = te, $fn = 48);
                    translate([s > 0 ? xe : -xe - te, -rc, 0]) cube([te, 2 * rc, tb]);
                }
                translate([s * xe, 0, zp]) rotate([0, -s * 90, 0]) hirth(180 / n_teeth);
            }
        }
        for (s = [-1, 1]) translate([s > 0 ? xe - 1 : -xe - te - 1, 0, zp]) rotate([0, 90, 0]) cylinder(d = m3_clear, h = te + 2, $fn = 24);
        for (s = [-1, 1]) translate([0, s * base_hole_y, 0]) {
            translate([0, 0, -1]) cylinder(d = m3_clear, h = tb + 2, $fn = 24);
            translate([0, 0, tb - 1.7]) cylinder(d1 = m3_clear, d2 = csk_d, h = 1.71, $fn = 32);
        }
    }
}

// the cradle on the base, tilted
module placed(t) { translate([0, 0, zp]) rotate([-t, 0, 0]) translate([0, 0, -zc]) children(); }
module ghost_sensor() {
    translate([-board[0] / 2, -board[1] / 2, so_h]) cube([board[0], board[1], board[2] + front]);
}

// a nicer sensor for the pictures only (the checks use ghost_sensor(), its envelope)
module look_sensor() {
    translate([-board[0] / 2, -board[1] / 2, so_h]) color([0.1, 0.35, 0.65]) cube(board);
    translate([0, 0, so_h + board[2]]) if (sensor == "hc") {
        for (x = [-13, 13]) translate([x, 0, 0]) color("silver") cylinder(d = 16, h = front, $fn = 48);
        translate([-3, -2, 0]) color("silver") cube([6, 4, 3]);
    } else color("black") translate([-1.5, -1.25, 0]) cube([3, 2.5, 1]);
}
module piece_colours() { color("white") base(); placed(tilt) { color("orange") cuna(); look_sensor(); } }

if (part == "base") base();
else if (part == "foto") piece_colours();
else if (part == "angulos") for (k = [0 : 3]) let(t = [-30, 0, 45, 90][k])
    translate([0, k * (sensor == "hc" ? 46 : 36), 0]) { color("white") base(); placed(t) { color("orange") cuna(); look_sensor(); } }
else if (part == "piezas") { color("white") base(); translate([0, (sensor == "hc" ? 40 : 32), 0]) color("orange") translate([0, 0, tp]) cuna(); }
else if (part == "cuna") translate([0, 0, tp]) cuna();
else if (part == "montado") { color("white") base(); placed(tilt) { color("orange") cuna(); color("blue") ghost_sensor(); } }
else if (part == "check_sweep") intersection() { base(); union() for (t = [-30 : 10 : 90]) placed(t) { cuna(); ghost_sensor(); } }
else if (part == "check_mesh") intersection() { base(); placed(tilt) cuna(); }
else if (part == "echo") { echo(zp = zp, width = 2 * (xe + te), base_l = base_l); cube(0.01); }
