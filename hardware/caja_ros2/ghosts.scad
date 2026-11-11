// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// "Ghosts": what goes inside the box, where it sits once assembled, including the room its
// plugs and cables need. The printed parts are tested against them: part ∩ ghost must be empty.
include <params.scad>

module box_from(p0, p1) { translate(p0) cube([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]); }

// --- Pico carrier board: vertical, parts facing the front --------------------------------
module ghost_pico() {
    x0 = pico_x0(); y = pico_y(); zt = pico_ztop(); zb = zt - pico_h;
    box_from([x0, y, zb], [x0 + pico_w, y + pcb_t, zt]);                    // the board
    box_from([x0, y + pcb_t, zb], [x0 + pico_w, y + pcb_t + 3, zt]);        // leads at the back
    // in front: Pico, headers and the Dupont plugs with their cables, all the way to the front
    // wall, except around the M3 holes (the front's columns) and in front of the OLED
    difference() {
        box_from([x0, wall + 0.5, zb], [x0 + pico_w, y, zt]);
        for (h = pico_holes) translate(pico2world(h[0], h[1]) + [0, 1, 0])
            rotate([90, 0, 0]) cylinder(d = 8.4, h = pico_gap + 2, $fn = 32);
        translate(pico2world(sw1[0], sw1[1]) - [0, pico_y() - wall, 0])      // the DISPLAY push rod's path
            rotate([-90, 0, 0]) cylinder(d = 9, h = pico_gap - sw1_h, $fn = 32);
        // in front of the OLED nothing is plugged: right of the EXP header's Dupont housings (they end at
        // bx 41.5) and below the last VL row's (by 52.3)
        translate([x0 + 42, wall, zt - pico_h]) cube([pico_w - 42, y - wall - oled_thick, pico_h - 54]);
    }
    // the Pico's micro-USB on the top edge, angled plug + cable
    box_from([x0 + 40 - 8, y - 16, zt], [x0 + 40 + 8, y, zt + pico_usb_clear - 0.5]);
    // 5 V terminal J1 and USB-C J5 on the left edge: their wires come in from the left
    box_from([wall + 0.5, wall + 0.5, zt - 82], [x0, y, zt - 50]);
    // side channels: the sensor cables (US1-5 left, VL1-4 right) run past the board's edges
    // to the back; nothing printed may sit in them
    for (xs = [[wall + 0.5, x0 - 0.8], [x0 + pico_w + 0.8, W - wall - 0.5]])
        box_from([xs[0], wall + 0.5, zb + 5], [xs[1], y + pcb_t + 3, zt]);
}

// --- Raspberry Pi 4: standing on its bracket, ports to the back -------------------------
module ghost_pi_pcb() {
    box_from([pi_x_pcb(), pi_y0(), pi_z0()], [pi_x_pcb() + pcb_t, pi_y0() + pi_l, pi_z0() + pi_w]);
}

module ghost_pi() {
    xp = pi_x_pcb(); y0 = pi_y0(); z0 = pi_z0();
    box_from([xp, y0, z0], [xp + pcb_t, y0 + pi_l, z0 + pi_w]);             // the board
    difference() {                                                          // solder side, 2 mm
        box_from([xp + pcb_t, y0, z0], [xp + pcb_t + 2, y0 + pi_l, z0 + pi_w]);
        for (h = pi_holes) translate([xp, y0 + h[0], z0 + h[1]]) rotate([0, 90, 0])
            cylinder(d = 6, h = 10, $fn = 24);
    }
    box_from([xp - pi_fan_clear, y0, z0], [xp, y0 + pi_l, z0 + pi_w]);      // parts + fan
    pi_ports();
    // USB-C power plug on the top edge, 11.2 mm from the front edge
    box_from([xp - 10, y0 + 11.2 - 7, z0 + pi_w], [xp + 0.5, y0 + 11.2 + 7, z0 + pi_w + pi_usbc_clear]);
}

// the USB and Ethernet jacks (they also go into the back wall's cut-out); ext = extra length
module pi_ports(ext = 0) {
    xp = pi_x_pcb(); y0 = pi_y0(); z0 = pi_z0(); ye = y0 + pi_l + pi_port_out + ext;
    for (zc = [47, 29]) box_from([xp - 16, ye - 21 - ext, z0 + zc - 6.75], [xp, ye, z0 + zc + 6.75]);   // USB x2
    box_from([xp - 13.5, ye - 21 - ext, z0 + 10.25 - 8], [xp, ye, z0 + 10.25 + 8]);                     // Ethernet
}

// --- 24 -> 5 V converter on its bosses -------------------------------------------------
module ghost_conv() {
    p = [conv_pos[0], conv_pos[1], wall + conv_lift];
    box_from(p, p + conv);
    box_from([p[0] + conv_wire_x - 8, p[1] + conv[1], p[2] + 4],
             [p[0] + conv_wire_x + 8, p[1] + conv[1] + conv_wires, p[2] + 18]);              // wires
}

// --- XT60E-F and KCD1 on the back: the part behind the back wall --------------------------
module ghost_xt60() {
    yb = D - wall;
    box_from([xt60_c[0] - xt60_body[0] / 2, yb - xt60_depth, xt60_c[1] - xt60_body[1] / 2],
             [xt60_c[0] + xt60_body[0] / 2, yb, xt60_c[1] + xt60_body[1] / 2]);
    box_from([xt60_c[0] - xt60_body[0] / 2, yb - xt60_depth - 15, xt60_c[1] - xt60_body[1] / 2],
             [xt60_c[0] + xt60_body[0] / 2, yb - xt60_depth, xt60_c[1] + xt60_body[1] / 2]);   // wires
}

module ghost_switch() {
    yb = D - sw_panel_t;
    box_from([sw_c[0] - sw_cut[0] / 2 + 0.1, yb - sw_depth - sw_wires, sw_c[1] - sw_cut[1] / 2 + 0.1],
             [sw_c[0] + sw_cut[0] / 2 - 0.1, yb, sw_c[1] + sw_cut[1] / 2 - 0.1]);
}

// sensor cables from the side channels to the back slot (the Pico's USB cable goes out there too):
// left, high, straight back; right, over the Pi; then along the back wall to the slot
module ghost_cables() {
    x0 = pico_x0(); y1 = pico_y() + pcb_t + 3; yb = D - wall;
    zc = sensor_slot_c[1];
    box_from([wall + 0.5, y1, zc - 6], [x0 - 0.8, yb, zc + 6]);
    box_from([pi_x_pcb() + pcb_t + 0.5, y1, pi_z0() + pi_w + 2.5], [W - wall - 0.5, yb, pi_z0() + pi_w + 8]);   // over the bracket
    box_from([wall + 0.5, yb - 8, zc - 6], [sensor_slot_c[0] + sensor_slot[0] / 2, yb, zc + 6]);
}

module ghost(name) {
    if (name == "pico") ghost_pico();
    else if (name == "pi") ghost_pi();
    else if (name == "conv") ghost_conv();
    else if (name == "xt60") ghost_xt60();
    else if (name == "switch") ghost_switch();
    else if (name == "cables") ghost_cables();
    else assert(false, str("unknown ghost ", name));
}

module ghost_all() { for (g = ["pico", "pi", "conv", "xt60", "switch", "cables"]) ghost(g); }
