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
            rotate([90, 0, 0]) cylinder(d = 7, h = pico_gap + 2, $fn = 32);
        translate([x0 + oled_rect[0], wall, zt - oled_rect[3]])
            cube([oled_rect[2] - oled_rect[0], y - wall - oled_thick, oled_rect[3] - oled_rect[1]]);
    }
    // the Pico's micro-USB on the top edge, angled plug + cable
    box_from([x0 + 40 - 8, y - 16, zt], [x0 + 40 + 8, y, zt + pico_usb_clear - 0.5]);
    // 5 V terminal J1 and USB-C J5 on the left edge: their wires come in from the left
    box_from([wall + 0.5, wall + 0.5, zt - 82], [x0, y, zt - 50]);
}

// --- Raspberry Pi 4: standing on its bracket, ports to the back -------------------------
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
    box_from([p[0] - conv_wires, p[1] + 15, p[2]], [p[0], p[1] + 45, p[2] + conv[2]]);   // wires
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
    yb = D - wall;
    box_from([sw_c[0] - sw_cut[0] / 2 + 1, yb - sw_depth - sw_wires, sw_c[1] - sw_cut[1] / 2 + 1],
             [sw_c[0] + sw_cut[0] / 2 - 1, yb, sw_c[1] + sw_cut[1] / 2 - 1]);
}

module ghost(name) {
    if (name == "pico") ghost_pico();
    else if (name == "pi") ghost_pi();
    else if (name == "conv") ghost_conv();
    else if (name == "xt60") ghost_xt60();
    else if (name == "switch") ghost_switch();
    else assert(false, str("unknown ghost ", name));
}

module ghost_all() { for (g = ["pico", "pi", "conv", "xt60", "switch"]) ghost(g); }
