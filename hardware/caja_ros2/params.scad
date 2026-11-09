// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (mini torre): every measurement in one place.
// Axes: X width (looking at the front, left -> right), Y depth (front -> back), Z height.
// Origin: outer front-bottom-left corner of the box (mounting ears stick out beyond it).

// --- box -------------------------------------------------------------------------------
W = 107;                 // outer width
D = 133;                 // outer depth
H = 125;                 // outer height
wall = 2.5;              // every wall, floor and roof
fit = 0.25;              // clearance between printed parts that slide together
r_edge = 4;              // outer corner radius (vertical edges)

// --- fasteners -------------------------------------------------------------------------
insert_d = 4.0;          // hole for an M3 heat-set insert (M3 x 5.7)
insert_h = 6;
m3_clear = 3.4;          // M3 clearance hole
m3_head_d = 6.2;         // countersink diameter (M3 flat head)
m25_hole = 2.2;          // M2.5 screw straight into plastic (Pi standoffs)
mount_d = 4.3;           // ears that fix the box to the R2
boss_d = 8;              // round boss around an insert

// --- Pico carrier board (r2_pico_carrier, 80 x 90 x 1.6) --------------------------------
pico_w = 80;  pico_h = 90;  pcb_t = 1.6;
pico_gap = 30;           // board face -> inside of the front: pins 11.5 + Dupont 14 + cable bend
pico_usb_clear = 25;     // above the board's top edge: the Pico's micro-USB, angled 90 deg plug
pico_holes = [[3.5, 3.5], [76.5, 3.5], [3.5, 86.5], [76.5, 86.5]];   // M3, board coords
oled_rect = [44.85, 60, 72.15, 87.8];        // OLED module on the board (bx0, by0, bx1, by1)
oled_view = [58.5, 71];                      // centre of its visible area (board coords)
oled_win = [26, 15];                         // window in the front (X x Z)
oled_thick = 6;                              // OLED module height above the board

// --- Raspberry Pi 4 (85 x 56), standing in the YZ plane, parts facing -X -------------------
pi_l = 85;  pi_w = 56;
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];   // (along Y from the front edge, along Z from the bottom/GPIO edge)
standoff_pi = 6;         // bracket face -> Pi board
pi_fan_clear = 25;       // fan over the CPU, above the board
pi_usbc_clear = 30;      // above the board's top (USB-C) edge: straight USB-C plug
pi_port_out = 3;         // USB/Ethernet stick out past the board edge
bracket_t = 2.5;         // the Pi's vertical support wall

// --- 24 -> 5 V converter (65 x 57 x 23) on the floor --------------------------------------
conv = [65, 57, 23];
conv_lift = 4;           // bosses under its ears (room for the inserts)
conv_pos = [25, 39];     // its front-left corner (X, Y)
conv_wires = 15;         // room for its wires on its -X face

// --- back panel: XT60E-F + KCD1 rocker ---------------------------------------------------
xt60_flange = [15.8, 34];            // X x Z on the outside of the back
xt60_body = [10.5, 21.5];            // cut-out for the body
xt60_depth = 20.2;
xt60_hole_pitch = 25.4;              // between its 2 flange holes (measure it!)
xt60_c = [16, 25];                   // centre (X, Z)
sw_cut = [21, 15];                   // KCD1 cut-out (X x Z)
sw_depth = 20;  sw_wires = 12;
sw_c = [40, 15];                     // centre (X, Z)
sensor_slot = [35, 10];              // cable slot for the sensor wires (X x Z)
sensor_slot_c = [27.5, 100];

// --- logo ---------------------------------------------------------------------------------
logo_w = 80;
logo_depth = 0.6;
logo_zc = H - 22;                    // centre height of the logo on the front

// --- derived positions ---------------------------------------------------------------------
function pico_x0() = (W - pico_w) / 2;
function pico_y() = wall + pico_gap;                      // the board's front face
function pico_ztop() = H - wall - pico_usb_clear;         // the board's top (USB) edge
function pico2world(bx, by) = [pico_x0() + bx, pico_y(), pico_ztop() - by];
function oled_view_center() = [pico_x0() + oled_view[0], pico_ztop() - oled_view[1]];

function bracket_x() = W - wall - 0.5 - bracket_t;        // inner face of the Pi bracket
function pi_x_pcb() = bracket_x() - standoff_pi - pcb_t;  // the Pi board's component face
function pi_y0() = D - wall - pi_port_out - pi_l;         // the Pi's front edge
function pi_z0() = wall + conv_lift + conv[2] + 2.5;      // the Pi's bottom (GPIO) edge
function pi2world(py, pz) = [pi_x_pcb(), pi_y0() + py, pi_z0() + pz];
