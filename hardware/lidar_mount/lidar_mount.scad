// ROS2D2 - RPLIDAR C1 tilt mount, built on the real lidar base (baselidar.stl).
// The lidar hangs upside down under the base. Two ears on the base and the two wings of a U
// (screwed to the droid) each have an arc slot; one M4 bolt + wing nut per side runs through both
// slots, so the lidar tilts around the middle of the ears (the long slots allow far more than the
// lidar can turn before it touches the droid).
//
//   openscad -o lidar-base.stl -D 'part="base"' lidar_mount.scad
//   openscad -o lidar-u.stl    -D 'part="u"'    lidar_mount.scad
//   openscad -o lidar-mount-assembled.stl -D 'part="mount"' lidar_mount.scad
//   openscad -o assembly.png   -D 'part="assembly"' -D tilt=-20 lidar_mount.scad
//
// Units: mm. X = bolt axis (left-right), Y = towards the droid (+), Z = up.

part = "assembly";      // "base", "u" (in print orientation), "mount" (base + U, no lidar, no bolts),
                        // "mount_base" / "mount_u" (each alone, in the mount's position) or "assembly"
tilt = 0;               // assembly only: degrees, + = the lidar's front goes up, - = down

// ---------- the real base (baselidar.stl: 56.35 x 55.15 x 1.55, 4 x M2.5 at 43 x 43) ----------
BASE_W = 56.349;  BASE_D = 55.146;  BASE_T = 1.549;
CX = BASE_W / 2;  CY = BASE_D / 2;

// ---------- joint ----------
EAR_T    = 4;       // ear and wing thickness (X)
EAR_HALF = 16;      // half width of ears and wings (Y)
EAR_H    = 36;      // ear height above the plate
PC_Z     = BASE_T + 17;   // tilt centre: middle of the ears
SLOT_R   = 11;      // arc slot radius around the tilt centre
SLOT_W   = 4.4;     // M4 + play
SLOT_A_U   = 75;    // degrees each slot runs from the top towards the U's web
SLOT_A_OUT = 50;    // degrees each slot runs from the top away from the web
GAP      = 0.3;     // between an ear and its wing
GUSSET   = 5;       // stiffening fillet at the root of each ear (inside)

// ---------- U ----------
STANDOFF = 25;      // from the base's back edge to the U's web (lidar clears the droid down to about -30)
WEB_T    = 4;
M3       = 3.4;     // droid screws, countersunk
M3_HEAD  = 6.5;
M3_PITCH = 30;

YWEB = BASE_D + STANDOFF;          // inner face of the U's web
XW_L = -GAP - EAR_T;               // left wing, outer face
XW_R = BASE_W + GAP;               // right wing, inner face

$fn = 96;

// a 2D shape in (Y, Z) extruded EAR_T along X, starting at x
module side(x) { translate([x, 0, 0]) rotate([90, 0, 90]) linear_extrude(EAR_T) children(); }

module arc_slot() {   // around (CY, PC_Z), straight above at 0 degrees, SLOT_A_U towards the web, SLOT_A_OUT away
    for (a = [90 - SLOT_A_U : 1 : 90 + SLOT_A_OUT - 1])
        hull() for (b = [a, a + 1])
            translate([CY + SLOT_R * cos(b), PC_Z + SLOT_R * sin(b)]) circle(d = SLOT_W, $fn = 24);
}

module ear_2d() {
    difference() {
        hull() {
            translate([CY - EAR_HALF, BASE_T - 0.01]) square([2 * EAR_HALF, 0.01]);
            translate([CY, BASE_T + EAR_H - EAR_HALF]) circle(r = EAR_HALF);
        }
        arc_slot();
    }
}

module base() {
    // the real base, rebuilt from its own outline: baselidar.stl has 8 non-manifold edges (at the
    // right-hand holes) that CGAL refuses, and its top only wobbles 0.06 mm, so outline + thickness is it
    linear_extrude(BASE_T) projection() import("baselidar.stl", convexity = 4);
    // the ears sink 0.2 into the plate so they fuse with it
    translate([0, 0, -0.2]) {
        side(0) translate([0, 0.2]) ear_2d();
        side(BASE_W - EAR_T) translate([0, 0.2]) ear_2d();
    }
    // fillets on the inside of each ear's root (clear of the lidar's corner screws)
    for (x = [EAR_T, BASE_W - EAR_T])
        translate([x, CY - EAR_HALF + 2, BASE_T - 0.2])
            rotate([-90, 0, 0]) linear_extrude(2 * EAR_HALF - 4)
                polygon(x < CX ? [[0, 0], [GUSSET, 0], [0, -GUSSET]] : [[0, 0], [-GUSSET, 0], [0, -GUSSET]]);
}

module wing_2d() {
    difference() {
        hull() {
            translate([CY, PC_Z]) circle(r = EAR_HALF);
            translate([YWEB, PC_Z - EAR_HALF]) square([0.01, 2 * EAR_HALF]);
        }
        arc_slot();
    }
}

module u() {
    side(XW_L) wing_2d();
    side(XW_R) wing_2d();
    // web against the droid, two countersunk M3 (heads inside the U)
    difference() {
        translate([XW_L, YWEB - 0.01, PC_Z - EAR_HALF]) cube([XW_R + EAR_T - XW_L, WEB_T, 2 * EAR_HALF]);
        for (s = [-1, 1]) translate([CX + s * M3_PITCH / 2, 0, PC_Z]) rotate([-90, 0, 0]) {
            translate([0, 0, YWEB - 1]) cylinder(d = M3, h = WEB_T + 2, $fn = 32);
            translate([0, 0, YWEB - 0.02]) cylinder(d1 = M3_HEAD, d2 = M3, h = (M3_HEAD - M3) / 2, $fn = 32);
        }
    }
}

// rough RPLIDAR C1 (55.6 x 55.6 x 41.3), upside down under the base, for the assembly only
module lidar() {
    color("gray", 0.35) translate([CX, CY, 0]) {
        translate([-27.8, -27.8, -26]) cube([55.6, 55.6, 26]);
        translate([0, 0, -41.3]) cylinder(r = 25, h = 15.3);
    }
}
module bolts() {
    color("silver") for (x = [XW_L - 3, XW_R + EAR_T + 3])
        translate([x < CX ? x : x - (2 * EAR_T + 6 + GAP), CY, PC_Z + SLOT_R]) rotate([0, 90, 0])
            cylinder(d = 4, h = 2 * EAR_T + 6 + GAP, $fn = 24);
}

if (part == "base") base();
else if (part == "u") translate([0, 0, YWEB + WEB_T]) rotate([-90, 0, 0]) u();   // web on the bed
else if (part == "mount_base") translate([0, CY, PC_Z]) rotate([-tilt, 0, 0]) translate([0, -CY, -PC_Z]) base();
else if (part == "mount_u") u();
else if (part == "mount") { translate([0, CY, PC_Z]) rotate([-tilt, 0, 0]) translate([0, -CY, -PC_Z]) base(); u(); }
else {
    color("limegreen") translate([0, CY, PC_Z]) rotate([-tilt, 0, 0]) translate([0, -CY, -PC_Z]) { base(); lidar(); }
    color("royalblue") u();
    bolts();
}
