// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (rack). Pick what to render with part:
//   openscad -o wall.stl -D 'part="wall"' rack_box.scad
// Parts (print orientation): pared, logo_navy, logo_blue, logo_grey, wall_monocolor, pulsador, base, tapa,
// frame_pi4, frame_pi5; the LED face: wall_led, wall_led_monocolor, logo_navy_led,
// logo_blue_led, logo_grey_led; its translucent lenses: led_lenses; HDMI on the back: hdmi_holder
// (FPC kit holder) or hdmi_cover (blank cover); the LED face without AMS: wall_led_no_ams and its fillings
// inlay_navy, inlay_blue, inlay_grey; blanks for the unused connectors: blank (-D bi=0..9) or blanks_all.
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <wall.scad>
include <base.scad>
include <shell.scad>
include <frame.scad>
include <fasteners.scad>
include <light_pipes.scad>
include <hdmi_fpc.scad>
include <no_ams.scad>
include <blanks.scad>

part = "wall";
ga = "pico";  gb = "pi";  led = "VL1";
dz = 0;  press = 0;  colour = "navy";  kind = "all";  gap = 0;  model = "pi4";  leds = 0;  pp = "pared";  bi = 0;

module dot() { cube(0.01); }
module printed() { pared(); base(); tapa(); marco(model); }

if (part == "check_selftest") intersection() { cube(10); translate([10 + gap, 0, 0]) cube(10); }
else if (part == "check_selftest_two_touches") intersection() {
    union() { cube(10); translate([0, 0, 20]) cube(10); }
    union() { translate([10, 0, 0]) cube(10); translate([0, 10, 20]) cube(10); }
}
// --- ghosts ---
else if (part == "ghosts") ghost_all();
else if (part == "check_ghost_pair") intersection() { ghost(ga); ghost(gb); }
else if (part == "echo_layout") {
    echo("W", W); echo("D", D); echo("H", H); echo("wall", wall);
    echo("pi_port_face", pi_y0() + pi_l + pi_port_out);
    echo("pi_z0", pi_z0()); echo("pi_top", pi_z0() + pi_w); echo("conv_z0", conv_p0()[2]);
    echo("pico_gap", pico_gap); echo("top_tab_y", top_tab_y);
    echo("pico_zbot", pico_zbot()); echo("pico_usb_clear", pico_usb_clear);
    echo("xt60_x", xt60_c[0]); echo("sw_x", sw_c[0]); echo("div_x1", div_x[1]); echo("conv_y", conv_y);
    echo("xt60_z0", xt60_c[1] - xt60_flange[1] / 2);
    echo("n_leds", len(pico_leds)); echo("n_tubes", len([for (l = pico_leds) if (led_tube(l)) 1])); echo("lp_lens_n", lp_lens_n);
    echo("lp_bore", lp_bore); echo("lp_stem_d", lp_stem_d); echo("lp_hole", lp_hole); echo("lp_lens_d", lp_lens_d);
    dot();
}
// --- v3: diagnostics: one printed piece against one ghost ---
else if (part == "diag") intersection() {
    if (pp == "pared") pared(leds = true); else if (pp == "base") base(); else if (pp == "rod") pulsador(); else if (pp == "tapa") tapa();
    ghost(ga);
}
// --- v3: bays ---
else if (part == "check_bay_vs_dupont") intersection() { pared(leds = leds == 1); dupont_plugs(); }
else if (part == "check_bay_vs_pinch") intersection() { pared(leds = true); dupont_plugs(pinch, wall + 3); }
else if (part == "check_bay_vs_tubes") intersection() {
    bays_cut();
    union() { lp_tubes(); for (i = [0 : len(pico_leds) - 1]) lp_at(i) translate([0, 0, -1]) cylinder(d = lp_hole + 0.4, h = wall + 2, $fn = 48); }
}
else if (part == "check_bay_vs_keepouts") intersection() {
    bays_cut();
    union() { pico_columns(); rod_guide(); oled_tunnel(); scale([20, 1, 1]) oled_window(); }
}
// --- main face ---
// --- connector blanks ---
else if (part == "blank") print_blank(bi);
else if (part == "blanks_all") blanks_all();
else if (part == "blank_montado") blank(bi);
else if (part == "echo_blanks") { echo("blank_names", blank_names); echo("pico_x", pico_x()); echo("blank_air", blank_air); dot(); }
else if (part == "check_blank_vs_wall") intersection() { blank(bi); pared(leds = leds == 1); }
else if (part == "check_blank_pinch") intersection() {
    blank(bi);
    for (j = [0 : len(dupont_rows) - 1]) if (j != bi) let(r = dupont_rows[j], a = pico2world(r[2], r[3] + pinch), c = pico2world(r[0], r[1] - pinch))
        translate([-20, a[1], a[2]]) cube([wall + 3 + 20, c[1] - a[1], c[2] - a[2]]);
}
else if (part == "check_blank_pins") intersection() { blank(bi); blank_pins(bi); }
else if (part == "bays_slab") yz_to_face(0, wall) bays_2d();
else if (part == "check_bays_open_with_blanks") difference() { yz_to_face(0, wall) bays_2d(); for (i = [0 : len(dupont_rows) - 1]) blank(i); }
else if (part == "wall") print_pared() pared();
else if (part == "wall_monocolor") print_pared() pared(logo_depth_mono);
else if (part == "logo_navy") print_pared() logo_svg("navy");
else if (part == "logo_blue") print_pared() logo_svg("blue");
else if (part == "logo_grey") print_pared() logo_svg("grey");
else if (part == "logo_navy_montado") logo_svg("navy");
else if (part == "check_pared_vs_ghosts") intersection() { pared(); ghost_all(); }
else if (part == "echo_oled_view") {
    c = oled_view_center();
    echo("dist", pico_x() - oled_thick - wall);
    echo("win_inner", oled_win_inner());
    echo("active", [c[0] - oled_active[0] / 2, c[1] - oled_active[1] / 2, c[0] + oled_active[0] / 2, c[1] + oled_active[1] / 2]);
    dot();
}
else if (part == "logo_grey_montado") logo_svg("grey");
else if (part == "logo_todo_montado") logo_svg("todo");
else if (part == "check_window_vs_columns") intersection() { pico_columns(); scale([20, 1, 1]) oled_window(); }
else if (part == "check_guide_vs_window") intersection() { rod_guide(); scale([20, 1, 1]) oled_window(); }
else if (part == "check_columns_short") intersection() { pico_columns(0.2); ghost_pico_pcb(); }
else if (part == "check_columns_touch") intersection() { pico_columns(-0.2); ghost_pico_pcb(); }
else if (part == "check_logo_overlap") linear_extrude(1) union() {
    intersection() { logo_2d("navy"); logo_2d("blue"); }
    intersection() { logo_2d("navy"); logo_2d("grey"); }
    intersection() { logo_2d("blue"); logo_2d("grey"); }
}
// --- push rod ---
else if (part == "push_rod") print_rod() pulsador();
else if (part == "check_rod_vs_ghosts") intersection() { pulsador(); ghost_all(); }
else if (part == "check_rod_vs_pared") intersection() { pulsador(press); pared(); }
else if (part == "check_rod_on_button") intersection() {
    pulsador(press);
    s = sw1_world(); translate([pico_x() - sw1_h, s[1] - 3, s[2] - 3]) cube([sw1_h, 6, 6]);
}
// --- base ---
else if (part == "base") base();
else if (part == "check_base_vs_ghosts") intersection() { base(); ghost_all(); }
else if (part == "check_ports_clear") intersection() { base(); pi_ports(10); }
// --- back frame ---
else if (part == "frame_pi4") print_marco() marco("pi4");
else if (part == "frame_pi5") print_marco() marco("pi5");
else if (part == "check_marco_ports") intersection() { marco(model); pi_ports(10, model); }
else if (part == "check_marco_vs_ghosts") intersection() { marco(model); difference() { ghost_all(); pi_ports(10, "both"); } }
else if (part == "check_marco_vs_base") intersection() { marco(model); base(); }
else if (part == "check_marco_fills_window") let(w = marco_win()) difference() {   // window seen from behind, minus frame and jacks
    translate([w[0], D - wall, w[1]]) cube([w[2] - w[0], wall, w[3] - w[1]]);
    marco(model); pi_ports(10, model, port_m + 0.01);
    for (x = [w[0], w[2] - marco_fit]) translate([x, D - wall - 1, w[1]]) cube([marco_fit, wall + 2, w[3] - w[1]]);
    for (z = [w[1], w[3] - marco_fit]) translate([w[0], D - wall - 1, z]) cube([w[2] - w[0], wall + 2, marco_fit]);
}
else if (part == "check_hdmi_cut") intersection() { base(); ghost_hdmi(); }
// --- HDMI on the back without reprinting the base: FPC holder or blank cover ---
else if (part == "hdmi_holder") print_hdmi_holder() hdmi_holder();
else if (part == "hdmi_cover") print_hdmi_cover() hdmi_cover();
else if (part == "hdmi_holder_montado") hdmi_holder();
else if (part == "hdmi_cover_montada") hdmi_cover();
else if (part == "check_hdmi_holder_vs_base") intersection() { hdmi_holder(); base(); }
else if (part == "check_hdmi_cover_vs_base") intersection() { hdmi_cover(); base(); }
else if (part == "check_hdmi_holder_vs_marco") intersection() { hdmi_holder(); union() { marco("pi4"); marco("pi5"); } }
else if (part == "check_hdmi_cover_vs_marco") intersection() { hdmi_cover(); union() { marco("pi4"); marco("pi5"); } }
else if (part == "check_hdmi_holder_screws") intersection() { hdmi_holder(); hdmi_screw_axes(); }
else if (part == "check_hdmi_cover_screws") intersection() { hdmi_cover(); hdmi_screw_axes(); }
else if (part == "check_hdmi_cover_fills_window") difference() {
    hdmi_turned() translate([hdmi_c[0] - hdmi_body[0] / 2 - 0.3, D - wall, hdmi_c[1] - hdmi_body[1] / 2 - 0.3]) cube([hdmi_body[0] + 0.6, wall, hdmi_body[1] + 0.6]);
    base(); hdmi_cover();
    hdmi_turned() translate([hdmi_c[0] - hdmi_body[0] / 2 - 0.3, D - wall - 1, hdmi_c[1] - hdmi_body[1] / 2 - 0.3]) difference() {   // the 0.3 fit gap
        cube([hdmi_body[0] + 0.6, wall + 2, hdmi_body[1] + 0.6]);
        translate([0.3, -1, 0.3]) cube([hdmi_body[0], wall + 4, hdmi_body[1]]);
    }
    translate([0, D - wall - 1, 0]) cube([W, wall - cover_plug + 1, H]);   // the plug is shorter than the wall
}
else if (part == "check_xt60_flange_seat") intersection() { front_panel(); ghost_xt60(); }
else if (part == "check_xt60_cut") intersection() { front_panel(); ghost_xt60_lip(); }
else if (part == "check_switch_cut") intersection() { front_panel(); translate([0, -sw_depth - sw_wires, 0]) ghost_switch(); }
else if (part == "check_front_vs_ghosts") intersection() { front_panel(); ghost_all(); }
else if (part == "check_shell_lift") intersection() { translate([0, 0, dz]) tapa(); union() { front_panel(); ghost_xt60(); ghost_switch(); } }
else if (part == "check_pi_standoffs_touch") intersection() { pi_standoffs(0.2); ghost_pi_pcb(); }
else if (part == "check_base_vs_pared") intersection() { base(); pared(); }
// --- shell ---
else if (part == "shell") print_tapa() tapa();
else if (part == "check_tapa_assembled") intersection() { tapa(); union() { base(); pared(); } }
else if (part == "check_tapa_slide") intersection() { translate([0, 0, dz]) tapa(); union() { base(); pared(); } }
else if (part == "check_tapa_vs_ghosts") intersection() { tapa(); ghost_all(); }
else if (part == "check_usb_vs_shell") intersection() { tapa(); ghost("usb"); }
else if (part == "check_usb_vs_pared") intersection() { pared(leds = leds == 1); ghost("usb"); }
else if (part == "check_logo_vs_usb_recess") intersection() { logo_svg("todo", 1.4, false); usb_recess_cut(); }
else if (part == "check_tapa_vs_ghost") intersection() { tapa(); ghost(ga); }   // one ghost at a time: light enough for OpenSCAD 2021
else if (part == "echo_vents") echo_vents();
else if (part == "montaje_sin_orejetas") { pared(); base(); tapa(); }
// --- v3: removable ears ---
else if (part == "ear") ear();
else if (part == "ear_blank") ear_blank();
else if (part == "ears_mounted") ears_mounted();
else if (part == "echo_ears") {
    echo("sites", [for (s = ear_sites) [s[0], s[1]]]);
    echo("vertical_lug_planes", [for (s = ear_sites) if (s[1] == "vertical") ear_pt(s, [-ear_e, 0, -1])[2]]);
    echo("horizontal_lug_planes", [for (s = ear_sites) if (s[1] == "horizontal") ear_pt(s, [-ear_e, 0, -1])[0]]);
    echo("W", W); echo("lug_out", ear_lug);
    dot();
}
else if (part == "check_pads_vs_ghosts") intersection() { ear_pads(); ghost_all(); }
else if (part == "check_ears_vs_power") intersection() { ear_pockets(1); union() { on_front() { switch_cut(); xt60_cut(); } front_vents(); } }
else if (part == "check_ears_vs_back") intersection() { ear_pockets(1); union() { back_cuts(); insert_holes(); } }
else if (part == "check_ear_flush") union() {
    intersection() { ears_mounted(); union() { base(); pared(); tapa(); } }
    intersection() { blanks_mounted(); union() { translate([-1, -5, -1]) cube([W + 2, 5 - 0.01, H + 2]); translate([-1, D + 0.01, -1]) cube([W + 2, 5, H + 2]); } }
}
// --- light pipes ---
else if (part == "wall_led") print_pared() pared(leds = true);
else if (part == "wall_led_monocolor") print_pared() pared(logo_depth_mono, true);
// the cone version of the LED face and its lenses (same logos as wall_led)
else if (part == "wall_led_cone") let($lp_cone = true) print_pared() pared(leds = true);
else if (part == "wall_led_cone_monocolor") let($lp_cone = true) print_pared() pared(logo_depth_mono, true);
else if (part == "led_lenses_cone") let($lp_cone = true) led_lenses();
else if (part == "check_lentes_cone_vs_pared") let($lp_cone = true) intersection() { lentes_montadas(); pared(leds = true); }
else if (part == "check_lentes_cone_flush") let($lp_cone = true) intersection() { lentes_montadas(); translate([-5, 0, 0]) cube([4.99, D, H]); }
else if (part == "check_lp_cone_bores_open") let($lp_cone = true) intersection() {
    pared(leds = true);
    for (i = [0 : len(pico_leds) - 1]) if (led_tube(pico_leds[i])) lp_at(i) translate([0, 0, lp_lens_t + lp_stem_l + 0.1]) cylinder(d = lp_tip_bore - 0.2, h = lp_tip_x() + 1, $fn = 24);
}
else if (part == "echo_lp_cone") {
    echo("lc_z", lc_z); echo("lens_cone_end", lc_z + (lp_lens_d - lp_stem_d) / 2);
    echo("recess_cone_end", lp_lens_t + 0.05 + (lp_hole - lp_bore) / 2); echo("wall", wall); dot();
}
else if (part == "logo_navy_led") print_pared() logo_svg("navy", leds = true);
else if (part == "logo_blue_led") print_pared() logo_svg("blue", leds = true);
else if (part == "logo_grey_led") print_pared() logo_svg("grey", leds = true);
else if (part == "logo_todo_led_montado") logo_svg("todo", leds = true);
else if (part == "echo_lp_holes") {
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) echo(pico_leds[i][0], [w[1], w[2], lp_hole]);
    dot();
}
else if (part == "check_lp_holes_open") intersection() {
    pared(leds = true);
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) translate([-1, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d = lp_bore - 0.2, h = wall + 2, $fn = 24);
}
else if (part == "led_lenses") led_lenses();
else if (part == "lentes_montadas") lentes_montadas();
else if (part == "check_lentes_vs_pared") intersection() { lentes_montadas(); pared(leds = true); }
else if (part == "check_lentes_flush") intersection() { lentes_montadas(); translate([-5, 0, 0]) cube([4.99, D, H]); }
else if (part == "check_lp_bores_open") intersection() {     // each bore's core, wall to tube end: nothing of the face
    pared(leds = true);
    for (i = [0 : len(pico_leds) - 1]) if (led_tube(pico_leds[i])) lp_at(i) translate([0, 0, lp_lens_t + lp_stem_l + 0.1]) cylinder(d = lp_tip_bore - 0.2, h = lp_tip_x() + 1, $fn = 24);
}
else if (part == "check_lp_tubes_vs_pcb") intersection() { pared(leds = true); ghost_pico_pcb(); }
else if (part == "echo_lp_tips") {
    for (i = [0 : len(pico_leds) - 1]) if (led_tube(pico_leds[i])) echo(pico_leds[i][0], lp_tip_x());
    echo("column_end", pico_x() - 0.05);          // pico_columns() stop 0.05 short of the board's face
    i = search(["PICO"], pico_leds)[0];
    echo("pico_led_top", led_world(i)[0] - led_h); echo("stem_end", lp_lens_t + lp_stem_l); echo("wall", wall);
    dot();
}
else if (part == "check_lens_chamfer") intersection() {      // a ring at each mouth, 0.1 deep, out to 0.25 (the 45 deg chamfer is 0.3 there)
    pared(leds = true);
    for (i = [0 : len(pico_leds) - 1]) lp_at(i) translate([0, 0, -0.01]) difference() {
        cylinder(d = lp_hole + 2 * 0.25, h = 0.11, $fn = 48); translate([0, 0, -1]) cylinder(d = lp_hole - 0.2, h = 3, $fn = 48);
    }
}
else if (part == "check_pico_lens_vs_cuts") intersection() {  // 1 mm of face round the Pico LED's recess and chamfer
    let(i = search(["PICO"], pico_leds)[0]) lp_at(i) translate([0, 0, -1]) cylinder(d = lp_hole + 2 * lp_chamfer + 2, h = wall + 2, $fn = 48);
    union() { oled_window(); usb_recess_cut(); rod_hole(); bays_cut(); na_pockets(); }
}
else if (part == "check_wall_led_vs_ghosts") intersection() { pared(leds = true); ghost_all(); }
else if (part == "ghost_leds_only") ghost_leds();
else if (part == "check_led_ghost_at") let(i = search([led], pico_leds)[0], w = led_world(i))
    intersection() { ghost_leds(); translate([w[0] - 0.6, w[1] - 0.2, w[2] - 0.2]) cube([0.4, 0.4, 0.4]); }
else if (part == "check_vl_dupont_vs_vl_leds") intersection() {
    ghost_pico();
    for (i = [0 : 3]) let(w = led_world(i)) translate([w[0] - pico_gap + 1, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d = lp_tip_od, h = pico_gap - 1 - led_h - 0.01, $fn = 24);
}
else if (part == "echo_leds") {
    for (i = [0 : len(pico_leds) - 1]) echo(pico_leds[i][0], led_world(i));
    echo("lp_tip_x", lp_tip_x()); echo("pico_x", pico_x()); echo("pico_ztop", pico_ztop());
    dot();
}
// --- LED face without AMS ---
else if (part == "wall_led_no_ams") print_pared() pared_no_ams();
else if (part == "inlay_navy") print_pared() relleno("navy");
else if (part == "inlay_blue") print_pared() relleno("blue");
else if (part == "inlay_grey") print_pared() relleno("grey");
else if (part == "inlay_montado") relleno(colour);
else if (part == "na_pockets_montados") na_pockets();
else if (part == "check_rellenos_vs_pared") intersection() { pared_no_ams(); union() for (c = logo_colours) relleno(c); }
else if (part == "check_rellenos_flush") intersection() { union() for (c = logo_colours) relleno(c); translate([-5, 0, 0]) cube([4.99, D, H]); }
else if (part == "check_rellenos_overlap") intersection() { relleno(colour); union() for (c = logo_colours) if (c != colour) relleno(c); }
else if (part == "check_rellenos_fill") difference() { na_pockets(na_depth - 0.01, -na_fit - 0.01); union() for (c = logo_colours) relleno(c); }
else if (part == "check_na_vs_holes") intersection() { na_pockets(wall, 0.3); lp_holes(); }
else if (part == "check_na_vs_window") intersection() { na_pockets(wall, 0.3); scale([20, 1, 1]) oled_window(); }
else if (part == "check_na_vs_cuts") intersection() { na_pockets(wall, 0.3); union() { rod_hole(); bays_cut(); } }
else if (part == "check_pared_no_ams_vs_ghosts") intersection() { pared_no_ams(); ghost_all(); }
else if (part == "check_pared_no_ams_same_inside") let(o = na_depth + 0.01) difference() {   // behind the pockets: the LED face, unchanged
    intersection() { pared(leds = true); translate([o, -1, -1]) cube([60, D + 2, H + 2]); }
    pared_no_ams();
}
else if (part == "check_wall_led_same_inside") let(o = na_depth + 0.01) difference() {
    intersection() { pared_no_ams(); translate([o, -1, -1]) cube([60, D + 2, H + 2]); }
    pared(leds = true);
}
// --- hardware ---
else if (part == "echo_bom") {
    for (k = ["ins_m3", "ins_m25", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_flat", "m3x10_pan", "nut_m3", "m25x6", "m4x12"]) echo(k, count_kind(k));
    echo("inserts_without_screw", inserts_without_screw());
    dot();
}
else if (part == "check_screws_vs_parts") intersection() { hardware(kind); printed(); }
else assert(false, str("unknown part ", part));
