// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Tilting mounts for the HC-SR04 and the VL53L0X (GY-VL53L0XV2): a flat base with 2 countersunk M3 holes
// and two ears, and a cradle the sensor board is glued to, pivoting on the ears. Nothing sticks out past
// the board: the ears sit under the plate, flush with its sides, and the cradle cheeks go inside them.
// One countersunk M3 per side is the axle, through the ear into a heat-set insert in the cheek; Hirth
// teeth on the ear and the cheek lock the angle every 10 deg.
// The axle height comes from the tilt range: the more the sensor has to turn, the higher it sits.
// Tilt tilt_min..tilt_max: 0 = the sensor looks straight out of the base, +90 = along it.
//   openscad -o base_hc.stl -D 'part="base"' -D 'sensor="hc"' -D tilt_min=-30 -D tilt_max=90 sensor_mounts.scad
// Axes: X along the axle, Y across, Z up from the base bottom.

sensor = "hc";            // "hc" | "vl"
part = "montado";         // base | cradle | montado | check_sweep | check_mesh | echo; pictures: photo | angles | parts
tilt = 0;
tilt_min = -30;           // range the mount must reach (multiples of 10)
tilt_max = 90;

// --- sensors: board X x Y x t, front height, window in the plate for the parts/pins on the back ----
function S(k) = sensor == "hc"
    ? [[45, 20, 1.5], 12, [41, 17]]          // HC-SR04: transducers 12 high
    : [[25, 10.6, 1.6], 2.5, [13, 9.6]];     // VL53L0X: glued on the ends
board = S()[0]; front = S()[1]; win = S()[2];

// --- common ------------------------------------------------------------------------------------
tp = 3;                    // cradle plate
m = 1;                     // plate margin round the board
pw = board[0] + 2 * m;  ph = board[1] + 2 * m;
rc = min(7, ph / 2);       // cheek / ear radius round the axle (never wider than the plate)
tc = 6;                    // cheek thickness (M3 insert 5.7)
ins3 = [4.0, 6];           // M3 insert hole
te = 4;                    // ear thickness
tb = 3;                    // base plate
n_teeth = 36;  t_ri = 2.6;  t_ro = rc - 0.5;  t_h = 0.8;   // Hirth: 10 deg
gap = t_h + 0.1;           // cheek face to ear face, teeth meshed
clr = 1;                   // plate bottom over the top of the ears
m3_clear = 3.4;  csk_d = 6.4;  csk_h = 1.7;  base_hole_y = 9;

xo = pw / 2;               // ear outer face = side of the plate
xe = xo - te;              // ear inner face
xc = xe - gap;             // cheek outer face
zc = -tp - rc - clr;       // axle in cradle coords (plate top z = 0, bottom -tp)
top = board[2] + front;    // highest point of the sensor over the plate

// the axle height over the base bottom: the cradle sweeps tilt_min..tilt_max without touching the base
corners = [for (y = [-ph / 2, ph / 2], z = [-tp, top]) [y, z - zc]];
function zlow(t) = min([for (c = corners) c[0] * sin(t) + c[1] * cos(t)]);   // rotate([-t,0,0]) sends +Z to +Y
zp = tb + max(rc + 0.5, -min([for (t = [tilt_min : 5 : tilt_max]) zlow(t)]) + 1);
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
            for (s = [-1, 1]) {
                hull() {                                                   // cheek under the plate
                    translate([s > 0 ? xc - tc : -xc, 0, zc]) rotate([0, 90, 0]) cylinder(r = rc, h = tc, $fn = 48);
                    translate([s > 0 ? xc - tc : -xc, -rc, -tp - 0.01]) cube([tc, 2 * rc, 0.02]);
                }
                translate([s * xc, 0, zc]) rotate([0, s * 90, 0]) hirth();
            }
        }
        // window for the parts and solder joints on the board back (glue on the rim)
        translate([0, 0, -tp - 1]) linear_extrude(tp + 2) offset(r = 1.5) offset(delta = -1.5) square(win, center = true);
        for (s = [-1, 1]) translate([s * (xc + t_h + 1), 0, zc]) rotate([0, -s * 90, 0]) cylinder(d = ins3[0], h = ins3[1] + t_h + 1, $fn = 24);
    }
}

// --- base -------------------------------------------------------------------------------------
module base() {
    difference() {
        union() {
            translate([-xo, -base_l / 2, 0]) cube([2 * xo, base_l, tb]);
            for (s = [-1, 1]) {
                hull() {
                    translate([s > 0 ? xe : -xo, 0, zp]) rotate([0, 90, 0]) cylinder(r = rc, h = te, $fn = 48);
                    translate([s > 0 ? xe : -xo, -rc, 0]) cube([te, 2 * rc, tb]);
                }
                translate([s * xe, 0, zp]) rotate([0, -s * 90, 0]) hirth(180 / n_teeth);
            }
        }
        for (s = [-1, 1]) translate([s * xo, 0, zp]) rotate([0, -s * 90, 0]) {   // axle, countersunk outside
            translate([0, 0, -1]) cylinder(d = m3_clear, h = te + 2, $fn = 24);
            translate([0, 0, -0.01]) cylinder(d1 = csk_d, d2 = m3_clear, h = csk_h, $fn = 32);
        }
        for (s = [-1, 1]) translate([0, s * base_hole_y, 0]) {
            translate([0, 0, -1]) cylinder(d = m3_clear, h = tb + 2, $fn = 24);
            translate([0, 0, tb - csk_h]) cylinder(d1 = m3_clear, d2 = csk_d, h = csk_h + 0.01, $fn = 32);
        }
    }
}

// the cradle on the base, tilted
module placed(t) { translate([0, 0, zp]) rotate([-t, 0, 0]) translate([0, 0, -zc]) children(); }
module ghost_sensor() { translate([-board[0] / 2, -board[1] / 2, 0]) cube([board[0], board[1], board[2] + front]); }

// a nicer sensor for the pictures only (the checks use ghost_sensor(), its envelope)
module look_sensor() {
    translate([-board[0] / 2, -board[1] / 2, 0]) color([0.1, 0.35, 0.65]) cube(board);
    translate([0, 0, board[2]]) if (sensor == "hc") {
        for (x = [-13, 13]) translate([x, 0, 0]) color("silver") cylinder(d = 16, h = front, $fn = 48);
        translate([-3, -2, 0]) color("silver") cube([6, 4, 3]);
    } else color("black") translate([-1.5, -1.25, 0]) cube([3, 2.5, 1]);
}

step = sensor == "hc" ? 55 : 40;
if (part == "base") base();
else if (part == "photo") { color("white") base(); placed(tilt) { color("orange") cuna(); look_sensor(); } }
else if (part == "angles") for (k = [0 : 3]) let(t = [tilt_min, 0, round((tilt_max + max(tilt_min, 0)) / 20) * 10, tilt_max][k])
    translate([0, k * step, 0]) { color("white") base(); placed(t) { color("orange") cuna(); look_sensor(); } }
else if (part == "parts") { color("white") base(); translate([0, step, 0]) color("orange") rotate([180, 0, 0]) cuna(); }
else if (part == "cradle") rotate([180, 0, 0]) cuna();          // plate on the bed, cheeks up
else if (part == "montado") { color("white") base(); placed(tilt) { color("orange") cuna(); color("blue") ghost_sensor(); } }
else if (part == "check_sweep") intersection() { base(); union() for (t = [tilt_min : 10 : tilt_max]) placed(t) { cuna(); ghost_sensor(); } }
else if (part == "check_mesh") intersection() { base(); placed(tilt) cuna(); }
else if (part == "echo") { echo(zp = zp, width = 2 * xo, depth = base_l, height0 = zp - zc + top); cube(0.01); }
