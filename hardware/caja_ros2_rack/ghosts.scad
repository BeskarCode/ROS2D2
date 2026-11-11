// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Ghosts of what goes inside (with the room their plugs and cables need), assembled positions.
// Printed parts are tested against them: part ∩ ghost must be empty.
include <params.scad>

module box_from(p0, p1) {        // any two opposite corners
    lo = [for (i = [0 : 2]) min(p0[i], p1[i])]; hi = [for (i = [0 : 2]) max(p0[i], p1[i])];
    translate(lo) cube(hi - lo);
}

// a box over a board rectangle (bx0..bx1, by0..by1), from the board face out to depth d (towards -X)
module on_board(bx0, by0, bx1, by1, d) {
    a = pico2world(bx1, by1); b = pico2world(bx0, by0);
    box_from([pico_x() - d, a[1], a[2]], [pico_x(), b[1], b[2]]);
}

module ghost_pico() {
    on_board(0, 0, pico_w, pico_h, -pcb_t);                       // the board (towards +X)
    translate([pcb_t, 0, 0]) on_board(0, 0, pico_w, pico_h, -3);  // leads at the back
    difference() {
        union() {
            on_board(0, 0, pico_w, pico_h, oled_thick);           // low parts, OLED
            on_board(0, 6, 14, 58, pico_gap - 0.5);               // US1-5 headers + Dupont
            on_board(50, 6, 80, 54, pico_gap - 0.5);              // VL1-4 (last row by 51: its Dupont housings end at 52.3)
            on_board(24, 65, 42, 73, pico_gap - 0.5);             // EXP header (its Dupont housings end at bx 41.5)
            on_board(29, 0, 51, 55, 13);                          // the Pico on its sockets
            on_board(0, 52, 11, 66, 11);                          // 5 V terminal J1
        }
        for (h = pico_holes) translate(pico2world(h[0], h[1]) + [1, 0, 0]) rotate([0, -90, 0])
            cylinder(d = 8.4, h = pico_gap + 2, $fn = 32);
        translate(pico2world(sw1[0], sw1[1]) + [-sw1_h, 0, 0]) rotate([0, -90, 0])   // push rod path
            cylinder(d = 9, h = pico_gap, $fn = 32);
    }
    // J1's wires come in over the board's bx = 0 edge
    a = pico2world(0, 66); b = pico2world(0, 52);
    box_from([pico_x() - 11, a[1], a[2]], [pico_x(), min(a[1] + 2.5, D - wall), b[2]]);
    // the Pico's micro-USB, angled plug, over the top edge
    u = pico2world(40, 0);
    box_from([pico_x() - 14, u[1] - 8, u[2]], [pico_x(), u[1] + 8, u[2] + pico_usb_clear - 0.5]);
}

module ghost_pico_pcb() { on_board(0, 0, pico_w, pico_h, -pcb_t); }

module ghost_pi_pcb() { box_from([pi_x_pcb(), pi_y0(), pi_z0()], [pi_x_pcb() + pcb_t, pi_y0() + pi_l, pi_z0() + pi_w]); }

// the jacks on the back edge; model = "pi4", "pi5" or "both" (the ghost: whichever goes in, it must fit)
module pi_ports(ext = 0, model = "both", m = 0) {
    xp = pi_xp(); z0 = pi_z0(); ye = pi_y0() + pi_l + pi_port_out + ext;
    ps = model == "pi4" ? pi4_ports : model == "pi5" ? pi5_ports : concat(pi4_ports, pi5_ports);
    for (p = ps) box_from([xp - m, ye - 21 - ext, z0 + p[1] - port_half(p[0]) - m],
                          [xp + port_tall(p[0]) + m, ye + m, z0 + p[1] + port_half(p[0]) + m]);
}

module ghost_pi() {
    xp = pi_x_pcb(); y0 = pi_y0(); z0 = pi_z0();
    ghost_pi_pcb();
    difference() {                                                      // solder side
        box_from([xp - 2, y0, z0], [xp, y0 + pi_l, z0 + pi_w]);
        for (h = pi_holes) translate([xp - 3, y0 + h[0], z0 + h[1]]) rotate([0, 90, 0]) cylinder(d = 7, h = 4, $fn = 24);   // keep-out round the holes (M2.5 insert standoffs, d 6.5)
    }
    box_from([xp + pcb_t, y0, z0], [xp + pcb_t + pi_fan_clear, y0 + pi_l, z0 + pi_w]);   // parts + fan
    pi_ports();
    // angled USB-C and micro-HDMI plugs under the bottom edge, their cables towards the divider's bottom pass
    box_from([xp, y0 + 11.2 - 7, z0 - pi_under + 0.5], [xp + pcb_t + 12, y0 + 11.2 + 7, z0]);
    box_from([xp, y0 + pi_hdmi0 - 7, z0 - pi_under + 0.5], [xp + pcb_t + 12, y0 + pi_hdmi0 + 7, z0]);
}

module ghost_hdmi() {        // the panel jack's body inside the back, Pico side
    box_from([hdmi_c[0] - hdmi_body[0] / 2, D - wall - hdmi_depth, hdmi_c[1] - hdmi_body[1] / 2],
             [hdmi_c[0] + hdmi_body[0] / 2, D - wall, hdmi_c[1] + hdmi_body[1] / 2]);
}

module ghost_conv() {
    p = conv_p0();
    box_from(p, p + conv);
    box_from([p[0] + 2, p[1] - conv_wires, p[2] + 24], [p[0] + 18, p[1], p[2] + 39]);   // wires out the front face
}

module ghost_xt60() {        // behind the main face, body + wires towards +X (under the Pico board)
    c = xt60_c;
    box_from([wall, c[0] - xt60_body[1] / 2, c[1] - xt60_body[0] / 2],
             [wall + xt60_depth - xt60_flange_t + 14, c[0] + xt60_body[1] / 2, c[1] + xt60_body[0] / 2]);
}

module ghost_switch() {      // behind the main face, its wires towards +X
    c = sw_c;
    box_from([wall, c[0] - sw_cut[0] / 2 + 0.1, c[1] - sw_cut[1] / 2 + 0.1],
             [wall + sw_depth + sw_wires, c[0] + sw_cut[0] / 2 - 0.1, c[1] + sw_cut[1] / 2 - 0.1]);
}

// sensor cables from the headers up to the slot; the Pico's USB cable to the notch in the back
module ghost_cables() {
    s = sensor_slot_c; n = usb_notch_c;
    box_from([wall + 0.5, s[0] - sensor_slot[0] / 2, pico_ztop() - 4], [pico_x() - 5, s[0] + sensor_slot[0] / 2, s[1] + 4]);
    box_from([n[0] - usb_notch[0] / 2, pico2world(40, 0)[1], n[1] - 6], [n[0] + usb_notch[0] / 2, D - wall, n[1] + 6]);
}

module ghost(name) {
    if (name == "pico") ghost_pico();
    else if (name == "pi") ghost_pi();
    else if (name == "conv") ghost_conv();
    else if (name == "xt60") ghost_xt60();
    else if (name == "switch") ghost_switch();
    else if (name == "cables") ghost_cables();
    else if (name == "hdmi") ghost_hdmi();
    else assert(false, str("unknown ghost ", name));
}

module ghost_all() { for (g = ["pico", "pi", "conv", "xt60", "switch", "cables", "hdmi"]) ghost(g); }
