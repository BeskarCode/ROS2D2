// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 · option C, "rack blade": every measurement in one place.
// Axes: X width (the blades stack along it), Y depth, Z height. Origin: outer corner at the bottom,
// on the main face (x = 0: OLED, logo, push rod, switch, sensor cable slot) and the narrow front (y = 0).

// --- box ---------------------------------------------------------------------------------
W = 78;  D = 95;  H = 145;           // 145: Pi low (plugs under it), converter high, 5 mm between them
zs = H - 127;                        // what the main face's top-referenced features moved up from the first 127 mm version
wall = 2.5;  fit = 0.25;

// --- fasteners (same hardware as the first box) --------------------------------------------
insert_d = 4.0;  insert_h = 6;  ins25_d = 3.6;  ins25_h = 5.5;      // M3 and M2.5 heat-set inserts (hole d, depth)
  m3_clear = 3.4;  m3_head_d = 6.2;  m25_hole = 2.2;  mount_d = 4.3;  boss_d = 8;

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
div_pass = [0, 62, 13];              // cable pass at the bottom, under the Pi (USB-C, HDMI): y from, y to, height
div_pass_top = [0, 10, 20, 45];      // pass for the converter's wires, in front of the Pico board: y from, y to, z from / to over the converter's bottom

// --- Pi 4: blade on the divider, parts towards +X, jacks flush with the back ----------------------
pi_l = 85;  pi_w = 56;
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];   // (along Y from its front edge, along Z from its bottom edge)
standoff_pi = 4;
pi_fan_clear = 25;
pi_under = 15;                       // USB-C edge down: room under it for the angled USB-C and micro-HDMI plugs
pi_port_out = 3;
pi_usb_tab = 0.5;                    // extra per side on each USB-A hole, along the board edge: the shell's side tabs
// jacks on the back edge, measured from the USB-C edge: [kind, centre]; Pi 4 and Pi 5 swap Ethernet and USB
pi4_ports = [["usb", 9], ["usb", 27], ["rj45", 45.75]];
pi5_ports = [["rj45", 10.2], ["usb", 29.1], ["usb", 47]];
function port_half(k) = k == "usb" ? 6.75 + pi_usb_tab : 8;          // along the board edge
function port_tall(k) = k == "usb" ? 16 : 13.5;                       // out of the board face
pi_hdmi0 = 26;                       // micro-HDMI 0 on the bottom edge, from the front edge (Pi 4 and Pi 5)
conv_gap = 5;                        // Pi's top edge -> converter

// --- back: one window for both Pis, closed by a swappable frame (marco_pi4 / marco_pi5) -------------
marco_t = 2;  marco_lip = 3.5;  marco_fit = 0.25;  marco_rim = 1.5;     // flange outside; rim of the plug around the jacks

// --- converter (RCNUN 63.7 x 57.6 x 22) on edge under the Pi -----------------------------------
conv = [22, 57.6, 63.7];             // X (thickness) x Y x Z (ears top and bottom)
conv_y = 20;                         // its front face (cable gland): the wires bend into the pass in front of it
conv_holes = [[26.3, 4.85], [26.3, 58.85]];  // ear holes on one line: (Y from its front face = cable side, Z from its bottom) - RCNUN drawing, checked by the user
conv_ear_t = 1.6;
conv_wires = 15;

// --- main face, low (under the Pico board): XT60E-F turned 90 deg and the KCD1 switch ------------------
xt60_flange = [15.8, 34];  xt60_body = [9.5, 17];  xt60_depth = 20.2;  xt60_hole_pitch = 25.4;
xt60_flange_t = 3;
xt60_c = [35, 8];                    // centre on the main face (Y, Z); flange 34 along Y, body 17 along Y x 9.5 along Z
sw_cut = [19.2, 13];  sw_panel_t = 2;  sw_depth = 20;  sw_wires = 12;
sw_c = [75, 9];                      // centre on the main face (Y, Z)
sensor_slot = [58, 10];  sensor_slot_c = [49, 113 + zs];     // on the main face (Y, Z), clear of the top columns
usb_notch = [16, 14];  usb_notch_c = [23, 114 + zs];         // micro-USB out the back (X, Z)

// --- logo (main face) -------------------------------------------------------------------------
logo_w = 80;  logo_h = 13.4;  logo_zc = 90 + zs;
logo_depth = 0.6;  logo_depth_mono = 1.0;
logo_colours = ["marino", "azul", "gris"];
LOGO_DIR = "../caja_ros2/logo/";
LOGO_SVG_W = 92;                     // the SVGs are drawn 92 mm wide for the first box: scaled to logo_w here

// --- light pipes (LED face, optional translucent piece) ---------------------------------------
// the Pico board's LEDs (bx, by on the board, from r2_pico_carrier.kicad_pcb): one per sensor connector + power
pico_leds = [["VL1", 72.6, 12], ["VL2", 72.6, 24], ["VL3", 72.6, 39], ["VL4", 72.6, 51],
             ["US1", 21, 12], ["US2", 21, 22], ["US3", 21, 32], ["US4", 21, 42], ["US5", 21, 52],
             ["PWR", 40.8, 59.5]];
led_h = 0.8;                         // 0603 LED height, the datasheet's highest
led_air = 0.7;                       // air between a pipe's tip and its LED (nominal): pushed in by the hooks' air,
                                     // on a board resting on the columns' ends (0.05 short), 0.3 still stays
lp_d = 3;                            // light pipe diameter
lp_hole = lp_d + 0.4;                // its hole in the LED face: 0.2 per side, goes in without forcing, no play
logo_zc_led = 27.5;                  // the LED face's logo: centred between the XT60/switch (Z 16) and the window's chamfer (Z 39)
lp_label_h = 3.5;  lp_label_gap = 1; // connector names beside their dots
lp_label_font = "Liberation Sans:style=Bold";
// the translucent piece: a flat frame against the wall's inside face holds the 10 rods; hooks on the wall
// snap over two ears on each side. The VL side sits towards the front (its Dupont housings start at Y 21)
lp_frame_t = 2;  lp_frame_gap = 0.05;            // frame thickness; air to the wall (it rests on it)
lp_vl_strip = [13.4, 19.4];  lp_us_strip = [66.5, 72];   // Y of the two columns of the frame
lp_strip_z = [69.5, 115.5];                       // Z of both columns (under the board's column at Z 117)
lp_bar_z = [68.85, 70.4];  lp_bar_t = 4;          // the cross bar: between the OLED tunnel (top Z 68.7) and the VL
                                                  // Dupont plugs (from Z 70.5); thicker in X to stay stiff
lp_pwr_arm = [48.3, 51.7];                        // Y of the arm down to the PWR rod (the tunnel ends at Y 48)
lp_hole_x = 7;                                    // the holes go this deep: through the tunnel's wall by PWR
lp_ear = [1.6, 6, 13.5];                          // ear: Y width, Z length, X of its top (a long post bends easily)
lp_hook_t = 1.4;  lp_hook_gap = 0.2;  lp_hook_lip = 0.6;  lp_hook_lip_h = 1;
lp_hook_air = 0.35;                               // ear top to lip: a sagging bridge face and 0.2 mm layers still click
lp_hook_root = 1.2;                               // chamfer at the post's root (it bends across the layers)
lp_hooks_z = [[79.5, 106.5], [77.5, 107.5]];      // VL side, US side
led_well_d = 4;                      // nothing but the LED within this circle round it (board ghost)

// --- derived ------------------------------------------------------------------------------------
function pico_x() = wall + pico_gap;                       // board's component face
function pico_ztop() = H - wall - pico_usb_clear;
function pico2world(bx, by) = [pico_x(), pico_y_hi - bx, pico_ztop() - by];
function oled_view_center() = [pico_y_hi - oled_view[0], pico_ztop() - oled_view[1]];   // (Y, Z) on the main face
function pi_x_pcb() = div_x[1] + standoff_pi;              // the Pi's solder face
function pi_y0() = D - pi_port_out - pi_l;
function pi_z0() = wall + pi_under;                         // low: the converter's heat goes up, away from it
function conv_p0() = [div_x[1], conv_y, H - wall - conv[2] - 0.3];   // high, under the roof
function pi_xp() = pi_x_pcb() + pcb_t;                       // the Pi's parts face
// the back window: all the jacks of both Pis + margin + the plug's rim  ([x0, z0, x1, z1])
function marco_win() = [pi_xp() - 0.5 - marco_rim, pi_z0() + 1.75 - 0.5 - marco_rim,
                        pi_xp() + 16 + 0.5 + marco_rim, pi_z0() + 54.25 + 0.5 + marco_rim];
function marco_screws() = let(w = marco_win(), xc = (w[0] + w[2]) / 2) [[xc, w[1] - 6], [xc, w[3] + 5]];   // (X, Z)

// --- HDMI panel jack on the back, Pico side, under the Pico board (cable from the Pi's HDMI 0) - MEASURE
hdmi_body = [16, 7];  hdmi_depth = 13;  hdmi_flange = [36, 12];  hdmi_pitch = 29;  hdmi_flange_t = 1;
hdmi_c = [20, 25];                   // centre on the back (X, Z)
