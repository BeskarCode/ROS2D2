// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The main face (x = 0..wall): the Pico board hangs from its 4 columns, the OLED shows through a
// chamfered window, the push rod reaches the DISPLAY button, the XT60 and the switch sit low under the board,
// the sensor cables leave through one slot at the top, the logo is inlaid in 4 colours.
// Every screw goes into a heat-set insert: the XT60's two from outside into inserts in small bosses behind it.
include <params.scad>

col_d = 8;
tab = [10, 9, 8];                                 // bottom tabs (X x Y x Z), insert from below
tab_y = [8, 58];
top_tab = [10, 10, 7];  top_tab_y = 75;           // under the roof, insert from above
xt60_boss = [7.5, 4.5];                           // d, length behind the wall (insert from outside, under the flange)

function sw1_world() = pico2world(sw1[0], sw1[1]);
// window (Y, Z) inner opening; its +Y edge stops short of the push rod's guide
function oled_win_inner() = let(c = oled_view_center(), r = sw1_world()[1] - guide_od / 2 - 1.6)
    [c[0] - oled_win[0] / 2, c[1] + oled_win_dz - oled_win[1] / 2, min(r, c[0] + oled_win[0] / 2), c[1] + oled_win_dz + oled_win[1] / 2];

// --- logo: SVG x runs towards -Y (to the right seen from outside), SVG y up ------------------------
module logo_clean() { offset(delta = -0.005) offset(delta = 0.005) children(); }
module logo_2d(c) {
    if (c == "todo") logo_clean() union() for (k = logo_colours) import(str(LOGO_DIR, "logo_", k, ".svg"));
    else logo_clean() import(str(LOGO_DIR, "logo_", c, ".svg"));
}
// leds: the LED face's logo, moved down under the OLED window; its navy body also carries the connector names
module logo_svg(c, depth = logo_depth, leds = false) {
    yL = D / 2 + logo_w / 2; zlo = (leds ? logo_zc_led : logo_zc) - logo_h / 2;
    multmatrix([[0, 0, -1, depth], [-1, 0, 0, yL], [0, 1, 0, zlo], [0, 0, 0, 1]])
        linear_extrude(depth) scale(logo_w / LOGO_SVG_W) logo_2d(c);
    if (leds && c == "marino") lp_labels(depth);
}

// --- pieces ----------------------------------------------------------------------------------------
module pico_columns(extra = 0) {
    for (h = pico_holes) translate(pico2world(h[0], h[1])) difference() {
        translate([-pico_gap, 0, 0]) rotate([0, 90, 0]) cylinder(d = col_d, h = pico_gap - 0.05 - extra, $fn = 40);
        translate([-insert_h, 0, 0]) rotate([0, 90, 0]) cylinder(d = insert_d, h = insert_h + 0.01, $fn = 24);
    }
}

module oled_window() {
    r = oled_win_inner();
    difference() {
        hull() {
            translate([wall - 0.01, r[0], r[1]]) cube([0.02, r[2] - r[0], r[3] - r[1]]);
            translate([-0.01, r[0] - wall, r[1] - wall]) cube([0.02, r[2] - r[0] + wall, r[3] - r[1] + 2 * wall]);
        }
        for (h = pico_holes) translate([-1, pico2world(h[0], h[1])[1], pico2world(h[0], h[1])[2]])
            rotate([0, 90, 0]) cylinder(d = col_d + 1, h = wall + 2, $fn = 40);
    }
}

// a tunnel from the window to the OLED: from outside only the screen shows, not the rest of the board.
// Its inside runs from the window's edges to the active area's (+ margin), so it never cuts the view.
tunnel_t = 1.2;  tunnel_m = 1;  tunnel_gap = 0.4;
function tunnel_far() = let(c = oled_view_center())
    [c[0] - oled_active[0] / 2 - tunnel_m, c[1] - oled_active[1] / 2 - tunnel_m, c[0] + oled_active[0] / 2 + tunnel_m, c[1] + oled_active[1] / 2 + tunnel_m];
module oled_tunnel() {
    r = oled_win_inner(); f = tunnel_far(); xe = pico_x() - oled_thick - tunnel_gap;
    module slab(q, x0, x1, g = 0) translate([x0, q[0] - g, q[1] - g]) cube([x1 - x0, q[2] - q[0] + 2 * g, q[3] - q[1] + 2 * g]);
    difference() {
        hull() { slab(r, wall - 0.01, wall, tunnel_t); slab(f, xe - 0.01, xe, tunnel_t); }
        hull() { slab(r, wall - 1, wall); slab(f, xe, xe + 1); }
    }
}

module rod_guide() {
    p = sw1_world();
    translate([0, p[1], p[2]]) rotate([0, 90, 0]) difference() {
        translate([0, 0, wall - 0.01]) cylinder(d = guide_od, h = guide_len + 0.01, $fn = 40);
        translate([0, 0, -1]) cylinder(d = rod_bore, h = wall + guide_len + 2, $fn = 32);
    }
}

module rod_hole() {
    p = sw1_world();
    translate([-1, p[1], p[2]]) rotate([0, 90, 0]) cylinder(d = rod_bore, h = wall + 2, $fn = 32);
}

function rod_end_x() = pico_x() - sw1_h - rod_gap;
module pulsador(press = 0) {
    p = sw1_world();
    x0 = -rod_proud + press; x1 = rod_end_x() + press; xf = wall + guide_len + press;
    translate([0, p[1], p[2]]) rotate([0, 90, 0]) {
        hull() {
            translate([0, 0, x0]) cylinder(d = rod_d - 1, h = 0.01, $fn = 32);
            translate([0, 0, x0 + 0.5]) cylinder(d = rod_d, h = x1 - x0 - 0.5, $fn = 32);
        }
        translate([0, 0, xf]) cylinder(d = rod_flange[0], h = rod_flange[1], $fn = 40);
        translate([0, 0, xf + rod_flange[1] - 0.01]) cylinder(d1 = rod_flange[0], d2 = rod_d, h = (rod_flange[0] - rod_d) / 2, $fn = 40);
    }
}
module print_rod() { p = sw1_world(); translate([0, 0, rod_end_x()]) rotate([0, 90, 0]) translate([0, -p[1], -p[2]]) children(); }

module switch_cut() {
    c = sw_c;
    translate([-1, c[0] - sw_cut[0] / 2, c[1] - sw_cut[1] / 2]) cube([wall + 2, sw_cut[0], sw_cut[1]]);
    translate([sw_panel_t, c[0] - sw_cut[0] / 2 - 3, max(c[1] - sw_cut[1] / 2 - 3, -1)])
        cube([wall, sw_cut[0] + 6, sw_cut[1] + 6]);
}

module xt60_cut() {
    c = xt60_c;
    translate([-1, c[0] - xt60_body[1] / 2, c[1] - xt60_body[0] / 2]) cube([wall + 2, xt60_body[1], xt60_body[0]]);
    for (s = [-1, 1]) translate([-0.01, c[0] + s * xt60_hole_pitch / 2, c[1]]) rotate([0, 90, 0]) cylinder(d = insert_d, h = insert_h, $fn = 24);
}
module xt60_bosses() {
    c = xt60_c;
    for (s = [-1, 1]) translate([wall - 0.01, c[0] + s * xt60_hole_pitch / 2, c[1]]) rotate([0, 90, 0])
        cylinder(d = xt60_boss[0], h = xt60_boss[1] + 0.01, $fn = 32);
}

module sensor_slot_cut() {
    s = sensor_slot_c;
    translate([-1, s[0], s[1]]) rotate([0, 90, 0]) hull() for (k = [-1, 1])
        translate([0, k * (sensor_slot[0] - sensor_slot[1]) / 2, 0]) cylinder(d = sensor_slot[1], h = wall + 2, $fn = 32);
}

module wall_tabs() {
    for (y = tab_y) translate([wall, y - tab[1] / 2, wall]) difference() {
        cube(tab);
        translate([tab[0] / 2, tab[1] / 2, -0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    }
    translate([wall, top_tab_y - top_tab[1] / 2, H - wall - top_tab[2]]) difference() {
        cube(top_tab);
        translate([top_tab[0] / 2, top_tab[1] / 2, top_tab[2] - insert_h + 0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    }
}

// leds: the LED face (a hole over each of the Pico board's LEDs, logo moved down, connector names)
module pared(depth = logo_depth, leds = false) {
    difference() {
        union() {
            cube([wall, D, H]);
            pico_columns();
            wall_tabs();
            xt60_bosses();
            rod_guide();
            oled_tunnel();
        }
        oled_window();
        rod_hole();
        switch_cut();
        xt60_cut();
        sensor_slot_cut();
        logo_svg("todo", depth, leds);
        if (leds) { lp_holes(); lp_labels(depth); }
    }
}

// print orientation: outer face on the bed
module print_pared() { translate([H, 0, 0]) rotate([0, -90, 0]) children(); }
