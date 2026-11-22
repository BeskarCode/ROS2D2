// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// IMU bracket: one piece for the Adafruit BNO085 (product 4754), screwed to the Pi itself, the box unchanged.
// It hangs from the Pi's two holes on the USB side (board x 61.5) on two M2.5 male-female standoffs, in the room
// between the Pi's parts and the shell, behind the fan. Two places for the IMU board, the same 4 holes:
//   the arm  (parallel to the Pi, its outer face): level with the box LYING on the shell's side
//   the shelf (under the Pi's bottom edge, the board hanging under it): level with the box STANDING
// Upside down or not does not matter: the console's calibration takes the IMU's resting attitude as zero.
// Prints on its end (the profile on the bed): no supports.

imu_board = [25.4, 22.86];           // Adafruit 4754 (Adafruit-BNO08x-PCB .brd): 4 holes, 2.5 drill
imu_holes = [20.32, 17.78];          // between hole centres, along the board's long and short sides
imu_standoff = 10;                   // M2.5 male-female standoffs on the Pi's two holes (Pi's parts face -> arm)
imu_boss_d = 4.6;  imu_boss_h = 4;     // the board stands this far off: room for its chip and STEMMA plugs
imu_arm_boss = 6.2;                  // on the arm: the board's chip side clears the Pi's 16 mm USB/RJ45 jacks
imu_t = 3;                           // arm and shelf thickness
imu_y = [52.5, 73.5];                // arm and shelf: after the fan (y 51), before the USB/RJ45 jacks (y 74)
imu_arm_yc = 62.3;                   // the arm's board: its bosses within the arm (jacks from y 74), the board past the fan (y 50)
imu_pi_holes = [[61.5, 3.5], [61.5, 52.5]];   // the Pi holes it hangs from (pi_holes, USB side)
imu_shelf_z = 12.5;                  // shelf's underside: its top 2 under the Pi's bottom edge
imu_shelf_x = [30.5, 57.5];          // the shelf: from near the divider to near the shell
function imu_arm_x() = pi_xp() + imu_standoff;
function imu_yc() = imu_arm_yc;          // the shelf's board at the same y: all bosses within the bracket's ends
function imu_arm_zc() = 45;          // the arm's IMU: between the two standoffs
function imu_shelf_xc() = (imu_shelf_x[0] + imu_shelf_x[1]) / 2;

// the 4 holes of a board centred at the origin, its long side along a, short along b (unit vectors in a plane)
module imu_hole_pattern(long_along_z = true) {
    for (i = [-1, 1], j = [-1, 1])
        translate(long_along_z ? [0, j * imu_holes[1] / 2, i * imu_holes[0] / 2] : [i * imu_holes[0] / 2, j * imu_holes[1] / 2, 0]) children();
}

module imu_bracket() {
    xa = imu_arm_x(); yc = imu_yc();
    zt = pi_z0() + max([for (h = imu_pi_holes) h[1]]) + 4;
    difference() {
        union() {
            translate([xa, imu_y[0], imu_shelf_z]) cube([imu_t, imu_y[1] - imu_y[0], zt - imu_shelf_z]);            // arm
            translate([imu_shelf_x[0], imu_y[0], imu_shelf_z]) cube([imu_shelf_x[1] - imu_shelf_x[0], imu_y[1] - imu_y[0], imu_t]);   // shelf
            // the arm's IMU bosses (outer face, +X): long side along Z
            translate([xa + imu_t, imu_arm_yc, imu_arm_zc()]) imu_hole_pattern(true) rotate([0, 90, 0]) cylinder(d = imu_boss_d, h = imu_arm_boss, $fn = 24);
            // the shelf's IMU bosses (underside): long side along X
            translate([imu_shelf_xc(), yc, imu_shelf_z]) imu_hole_pattern(false) mirror([0, 0, 1]) cylinder(d = imu_boss_d, h = imu_boss_h, $fn = 24);
        }
        // M2.5 through the arm into each standoff
        for (h = imu_pi_holes) translate([xa - 1, pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, 90, 0]) cylinder(d = 2.8, h = imu_t + 2, $fn = 24);
        // the IMU's M2.5 screws bite into the bosses (2.2 holes, like the Pico's)
        translate([xa - 1, imu_arm_yc, imu_arm_zc()]) imu_hole_pattern(true) rotate([0, 90, 0]) cylinder(d = m25_hole, h = imu_t + imu_arm_boss + 2, $fn = 20);
        translate([imu_shelf_xc(), yc, imu_shelf_z + imu_t + 1]) imu_hole_pattern(false) mirror([0, 0, 1]) cylinder(d = m25_hole, h = imu_t + imu_boss_h + 2, $fn = 20);
    }
}

// the standoffs and the IMU board in each place, for the checks
module ghost_imu_standoffs() for (h = imu_pi_holes) translate([pi_xp(), pi_y0() + h[0], pi_z0() + h[1]]) rotate([0, 90, 0]) cylinder(d = 5, h = imu_standoff, $fn = 6);
module ghost_imu_arm() {             // the board + 3 mm of parts each side
    translate([imu_arm_x() + imu_t + imu_arm_boss - 3, imu_arm_yc - imu_board[1] / 2, imu_arm_zc() - imu_board[0] / 2]) cube([pcb_t + 6, imu_board[1], imu_board[0]]);
}
module ghost_imu_shelf() {
    translate([imu_shelf_xc() - imu_board[0] / 2, imu_yc() - imu_board[1] / 2, imu_shelf_z - imu_boss_h - pcb_t - 3]) cube([imu_board[0], imu_board[1], pcb_t + 6]);
}

// print on its end: the profile (X-Z) on the bed
module print_imu_bracket() translate([0, 0, imu_y[1]]) rotate([-90, 0, 0]) children();   // rotated: z = imu_y[1] - y
