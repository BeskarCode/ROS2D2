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
oled_win = [40, 26];                         // window, inner opening (X x Z): +-20 deg across, >=15 deg up/down
oled_win_dz = 1;                             // window raised 1 mm: keeps it clear of the lower column
oled_active = [22, 11];                      // visible area of a 0.96 in SSD1306
oled_thick = 6;                              // OLED module height above the board
sw1 = [38, 79];                              // the DISPLAY button SW1 (board coords)
sw1_h = 5;                                   // its height above the board (6x6 tact switch): MEASURE it
rod_d = 4.6;  rod_bore = 5.2;                // push rod and its hole through the front
guide_od = 7.2;  guide_len = 8;              // short guide tube behind the front
rod_flange = [7, 1.5];                       // stop collar: keeps the rod from falling out the front
rod_proud = 1;                               // tip out of the front at rest
rod_gap = 0.3;                               // rod end -> button at rest

// --- Raspberry Pi 4 (85 x 56), standing in the YZ plane, parts facing -X -------------------
pi_l = 85;  pi_w = 56;
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];   // (along Y from the front edge, along Z from the bottom/GPIO edge)
standoff_pi = 6;         // bracket face -> Pi board
pi_fan_clear = 25;       // fan over the CPU, above the board
pi_usbc_clear = 30;      // above the board's top (USB-C) edge: straight USB-C plug
pi_port_out = 3;         // USB/Ethernet stick out past the board edge
bracket_t = 2.5;         // the Pi's vertical support wall

// --- 24 -> 5 V converter (RCNUN, 63.7 x 57.6 x 22 with its ears) on the floor ---------------
// drawing: cajaROS2/transformador.PNG. Ears on the 63.7 side (X here); wires out of a long face (+Y)
conv = [63.7, 57.6, 22];
conv_lift = 5;           // bosses under its ears (room for the inserts, floor left under them)
conv_holes = [[3.6, 26.3], [60.1, 31.3]];  // its 2 ear holes from its front-left corner (drawing; 3.6 from the ear tip assumed)
conv_ear_t = 1.6;        // ear thickness (drawing)
conv_wire_x = 35;        // where its cable gland is, from its left end
conv_pos = [25, 39];     // its front-left corner (X, Y)
conv_wires = 15;         // room for its wires out of its +Y face

// --- back panel: XT60E-F + KCD1 rocker ---------------------------------------------------
xt60_flange = [15.8, 34];            // X x Z on the outside of the back
xt60_body = [9.5, 17];               // cut-out for the body (X x Z; housing ~8.3 x 16): measure it
xt60_depth = 20.2;
xt60_hole_pitch = 25.4;              // between its 2 flange holes (measure it!)
xt60_c = [16, 25];                   // centre (X, Z)
sw_cut = [19.2, 13];                 // KCD1 panel hole (X x Z; the bezel is 21 x 15): measure it
sw_panel_t = 2;                      // the back is thinned to this round the switch, for its clips
sw_depth = 20;  sw_wires = 12;
sw_c = [40, 15];                     // centre (X, Z)
sensor_slot = [35, 10];              // cable slot for the sensor wires (X x Z)
sensor_slot_c = [27.5, 100];

// --- top tabs: the front and the back hang on the roof (one M3 each, insert from above) -----
top_tab = [10, 8, 7];                // X x Y x Z, under the roof, centred in X
function top_tab_y() = [wall + top_tab[1] / 2, D - wall - top_tab[1] / 2];
// gusset = 1: a 45 deg support under it, from the wall behind it (+Y side)
module top_tab(y, gusset = 0) {
    translate([W / 2 - top_tab[0] / 2, y - top_tab[1] / 2, H - wall - top_tab[2]]) difference() {
        union() {
            cube(top_tab);
            if (gusset != 0) hull() {
                cube([top_tab[0], top_tab[1], 0.01]);
                translate([0, top_tab[1] - 0.01, -top_tab[1]]) cube([top_tab[0], 0.01, 0.01]);
            }
        }
        translate([top_tab[0] / 2, top_tab[1] / 2, top_tab[2] - insert_h + 0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    }
}

// --- side vents (U shell) and the matching slots in the Pi bracket -------------------------
slot_w = 2;  slot_pitch = 4.5;
side_band_low = [8, 30];
side_band_high = [H - 35, H - 8];
side_slot_y = [14, D - 14];
screw_keepout = 7;
shell_screw_ys = [20, D - 25];
function side_slots_y() = [for (y = [side_slot_y[0] : slot_pitch : side_slot_y[1] - slot_w])
    if (min([for (s = shell_screw_ys) abs(y + slot_w / 2 - s)]) > screw_keepout) y];

// --- logo ---------------------------------------------------------------------------------
logo_w = 92;                         // the GitHub logo (media/ros2d2-logo.png), without its tagline
logo_h = 15.4;
logo_colours = ["marino", "azul", "gris"];   // inlays; the panel itself is white
logo_depth = 0.6;
logo_depth_mono = 1.0;              // single-colour front (no AMS): logo engraved this deep
logo_zc = H - 22;                    // centre height of the logo on the front

// --- derived positions ---------------------------------------------------------------------
function pico_x0() = (W - pico_w) / 2;
function pico_y() = wall + pico_gap;                      // the board's front face
function pico_ztop() = H - wall - pico_usb_clear;         // the board's top (USB) edge
function pico2world(bx, by) = [pico_x0() + bx, pico_y(), pico_ztop() - by];
function oled_view_center() = [pico_x0() + oled_view[0], pico_ztop() - oled_view[1]];

function bracket_x() = W - wall - 0.5 - bracket_t;        // inner face of the Pi bracket
function pi_x_pcb() = bracket_x() - standoff_pi - pcb_t;  // the Pi board's component face
function pi_y0() = D - pi_port_out - pi_l;                // the Pi's front edge: its jacks end flush with the outside of the back
function pi_z0() = wall + conv_lift + conv[2] + 2.5;      // the Pi's bottom (GPIO) edge
function pi2world(py, pz) = [pi_x_pcb(), pi_y0() + py, pi_z0() + pz];
