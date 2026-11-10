// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 · option C, "rack blade": every measurement in one place.
// Axes: X width (the blades stack along it), Y depth, Z height. Origin: outer corner at the bottom,
// on the main face (x = 0: OLED, logo, push rod, switch, sensor cable slot) and the narrow front (y = 0).

// --- box ---------------------------------------------------------------------------------
W = 78;  D = 95;  H = 127;
wall = 2.5;  fit = 0.25;

// --- fasteners (same hardware as the first box) --------------------------------------------
insert_d = 4.0;  insert_h = 6;  m3_clear = 3.4;  m3_head_d = 6.2;  m25_hole = 2.2;  mount_d = 4.3;  boss_d = 8;

// --- Pico carrier board: vertical blade, parts towards the main face (-X) ------------------
pico_w = 80;  pico_h = 90;  pcb_t = 1.6;
pico_gap = 30;                       // main face (inside) -> board: Dupont plugs
pico_usb_clear = 18;                 // over its top edge: angled micro-USB
pico_holes = [[3.5, 3.5], [76.5, 3.5], [3.5, 86.5], [76.5, 86.5]];
oled_rect = [44.85, 60, 72.15, 87.8];
oled_view = [58.5, 71];
oled_active = [22, 11];
oled_thick = 6;
oled_win = [40, 26];                 // inner opening (along Y x Z); the side by the push rod is cut back
oled_win_dz = 1;
sw1 = [38, 79];  sw1_h = 5;
rod_d = 4.6;  rod_bore = 5.2;  guide_od = 7.2;  guide_len = 8;  rod_flange = [7, 1.5];  rod_proud = 1;  rod_gap = 0.3;
pico_y_hi = 90;                      // y of the board's bx = 0 edge (bx grows towards -Y: reads left to right from outside)

// --- central divider: holds the Pi and the converter -----------------------------------------
div_x = [37.6, 44];                  // 0.5 behind the Pico board's leads; 6.4 thick for M3 inserts
div_pass = [55, 80, 13];             // cable pass at the bottom: y from, y to, height

// --- Pi 4: blade on the divider, parts towards +X, jacks flush with the back ----------------------
pi_l = 85;  pi_w = 56;
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];   // (along Y from its front edge, along Z from its bottom edge)
standoff_pi = 4;
pi_fan_clear = 25;
pi_usbc_clear = 25;                  // USB-C edge down: the plug hangs into the gap in front of the converter
pi_port_out = 3;

// --- converter (RCNUN 63.7 x 57.6 x 22) on edge under the Pi -----------------------------------
conv = [22, 57.6, 63.7];             // X (thickness) x Y x Z (ears top and bottom)
conv_y = 26;                         // its front face (cable gland) - clear of the Pi's USB-C plug
conv_holes = [[26.3, 3.6], [31.3, 60.1]];   // ear holes: (Y from its front face, Z from its bottom) - CHECK
conv_ear_t = 1.6;
conv_wires = 15;

// --- main face, low (under the Pico board): XT60E-F turned 90 deg and the KCD1 switch ------------------
xt60_flange = [15.8, 34];  xt60_body = [9.5, 17];  xt60_depth = 20.2;  xt60_hole_pitch = 25.4;
xt60_flange_t = 3;
xt60_c = [35, 8];                    // centre on the main face (Y, Z); flange 34 along Y, body 17 along Y x 9.5 along Z
sw_cut = [19.2, 13];  sw_panel_t = 2;  sw_depth = 20;  sw_wires = 12;
sw_c = [75, 9];                      // centre on the main face (Y, Z)
sensor_slot = [58, 10];  sensor_slot_c = [49, 113];     // on the main face (Y, Z), clear of the top columns
usb_notch = [16, 14];  usb_notch_c = [23, 114];         // micro-USB out the back (X, Z)

// --- logo (main face) -------------------------------------------------------------------------
logo_w = 80;  logo_h = 13.4;  logo_zc = 90;
logo_depth = 0.6;  logo_depth_mono = 1.0;
logo_colours = ["marino", "azul", "gris"];
LOGO_DIR = "../caja_ros2/logo/";
LOGO_SVG_W = 92;                     // the SVGs are drawn 92 mm wide for the first box: scaled to logo_w here

// --- derived ------------------------------------------------------------------------------------
function pico_x() = wall + pico_gap;                       // board's component face
function pico_ztop() = H - wall - pico_usb_clear;
function pico2world(bx, by) = [pico_x(), pico_y_hi - bx, pico_ztop() - by];
function oled_view_center() = [pico_y_hi - oled_view[0], pico_ztop() - oled_view[1]];   // (Y, Z) on the main face
function pi_x_pcb() = div_x[1] + standoff_pi;              // the Pi's solder face
function pi_y0() = D - pi_port_out - pi_l;
function pi_z0() = H - wall - pi_w - 0.3;                  // top edge just under the roof
function conv_p0() = [div_x[1], conv_y, wall];
