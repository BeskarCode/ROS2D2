// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The main face (x = 0..wall): the Pico board hangs from its 4 columns, the OLED shows through a
// chamfered window, the push rod reaches the DISPLAY button, the XT60 and the switch sit low under the board,
// every sensor's Dupont plugs in from outside through a bay over its connectors, the logo is inlaid in 4 colours.
// Every screw goes into a heat-set insert but the XT60's two: through the wall and its flange into nuts.
include <params.scad>

col_d = 8;
tab = [10, 9, 8];                                 // bottom tabs (X x Y x Z), insert from below
tab_y = [8, 58];
top_tab = [10, 10, 7];  top_tab_y = [75, 20];     // under the roof, insert from above

function sw1_world() = pico2world(sw1[0], sw1[1]);
// window (Y, Z) inner opening; its +Y edge stops short of the push rod's guide and of the PWR lens's whole ring
function pwr_ring_edge() = let(i = search(["PWR"], pico_leds)[0]) pico2world(pico_leds[i][1], pico_leds[i][2])[1] - lp_ring_d() / 2;
function oled_win_inner() = let(c = oled_view_center(), r = min(sw1_world()[1] - guide_od / 2 - 1.6, pwr_ring_edge()))
    [c[0] - oled_win[0] / 2, c[1] + oled_win_dz - oled_win[1] / 2, min(r, c[0] + oled_win[0] / 2), c[1] + oled_win_dz + oled_win[1] / 2];

// --- logo: SVG x runs towards -Y (to the right seen from outside), SVG y up ------------------------
module logo_clean() { offset(delta = -0.005) offset(delta = 0.005) children(); }
module logo_2d(c) {
    if (c == "todo") logo_clean() union() for (k = logo_colours) import(str(LOGO_DIR, "logo_", k, ".svg"));
    else logo_clean() import(str(LOGO_DIR, "logo_", c, ".svg"));
}
// leds: the LED face's logo, moved down under the OLED window
module logo_svg(c, depth = logo_depth, leds = false) {
    yL = D / 2 + logo_w / 2; zlo = (leds ? logo_zc_led : logo_zc) - logo_h / 2;
    multmatrix([[0, 0, -1, depth], [-1, 0, 0, yL], [0, 1, 0, zlo], [0, 0, 0, 1]])
        linear_extrude(depth) scale(logo_w / LOGO_SVG_W) logo_2d(c);
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

// --- bays: an opening over each group of connectors, every Dupont plugs in from outside ------------------
function bay_yz(b) = let(a = pico2world(b[3], b[4]), c = pico2world(b[1], b[2])) [a[1], a[2], c[1], c[2]];   // y0, z0, y1, z1
module yz_to_face(x0, h) translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(h) children();   // 2D (Y, Z) -> slab along +X
module bay_keepouts_2d() {
    for (h = pico_holes) let(p = pico2world(h[0], h[1])) translate([p[1], p[2]]) circle(d = col_d + 2 * bay_keep, $fn = 40);
    for (l = pico_leds) let(p = pico2world(l[1], l[2])) translate([p[1], p[2]]) circle(d = lp_ring_d(), $fn = 40);   // the land is its own margin
    let(p = sw1_world()) translate([p[1], p[2]]) circle(d = guide_od + 2 * bay_keep, $fn = 40);
    // the OLED window (chamfered on -Y and in Z) and its tunnel's wall on +Y
    let(r = oled_win_inner(), g = wall + bay_keep)
        translate([r[0] - g, r[1] - g]) square([r[2] - r[0] + g + tunnel_t + 0.1, r[3] - r[1] + 2 * g]);
}
module bays_2d() offset(r = bay_r) offset(delta = -bay_r) difference() {
    union() for (b = pico_bays) let(q = bay_yz(b)) translate([q[0], q[1]]) square([q[2] - q[0], q[3] - q[1]]);
    bay_keepouts_2d();
}
module bays_cut() yz_to_face(-1, wall + 2) bays_2d();
// mated Dupont housings from the header's plastic out through the face (out = how far past x = 0)
module dupont_plugs(grow = 0, x_in = undef, out = 20) for (r = dupont_rows) let(a = pico2world(r[2], r[3] + grow), c = pico2world(r[0], r[1] - grow))
    translate([-out, a[1], a[2]]) cube([(x_in == undef ? pico_x() - 2.5 : x_in) + out, c[1] - a[1], c[2] - a[2]]);

module wall_tabs() {
    for (y = tab_y) translate([wall, y - tab[1] / 2, wall]) difference() {
        cube(tab);
        translate([tab[0] / 2, tab[1] / 2, -0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    }
    for (y = top_tab_y) translate([wall, y - top_tab[1] / 2, H - wall - top_tab[2]]) difference() {
        cube(top_tab);
        translate([top_tab[0] / 2, top_tab[1] / 2, top_tab[2] - insert_h + 0.01]) cylinder(d = insert_d, h = insert_h, $fn = 24);
    }
}

// leds: the LED face (a tube from each of the Pico board's LEDs, lens recesses, logo moved down, connector names)
// noams: logo and names as deep pockets for fillings printed apart (no_ams.scad)
// the straight micro-USB's overmould passes 1 mm into the face: thin it there, from inside
module usb_recess_cut() {
    u = pico2world(40, 0);
    translate([wall - usb_recess, u[1] - usb_plug[1] / 2 - 0.5, u[2] - 0.5])
        cube([usb_recess + 0.01, usb_plug[1] + 1, H - wall - u[2] + 0.5 + 0.01]);
}

module pared(depth = logo_depth, leds = false, noams = false) {
    difference() {
        union() {
            cube([wall, D, H]);
            pico_columns();
            wall_tabs();
            rod_guide();
            oled_tunnel();
            if (leds) lp_tubes();
        }
        oled_window();
        rod_hole();
        bays_cut();
        usb_recess_cut();
        if (noams) na_pockets(); else logo_svg("todo", depth, leds);
        if (leds) lp_holes();
    }
}

// print orientation: outer face on the bed
module print_pared() { translate([H, 0, 0]) rotate([0, -90, 0]) children(); }
