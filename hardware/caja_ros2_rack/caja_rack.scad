// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 · option C, "rack blade". Pick what to render with part:
//   openscad -o pared.stl -D 'part="pared"' caja_rack.scad
// Parts (print orientation): pared, logo_marino, logo_azul, logo_gris, pared_monocolor, pulsador, base, tapa,
// marco_pi4, marco_pi5, prueba_luz; the LED face: pared_led, pared_led_monocolor, logo_marino_led,
// logo_azul_led, logo_gris_led; the optional light-pipe piece: guias_luz.
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <pared.scad>
include <base.scad>
include <tapa.scad>
include <marco.scad>
include <fasteners.scad>
include <guias.scad>

part = "pared";
ga = "pico";  gb = "pi";  led = "VL1";
dz = 0;  press = 0;  kind = "all";  gap = 0;  model = "pi4";

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
    dot();
}
// --- main face ---
else if (part == "pared") print_pared() pared();
else if (part == "pared_monocolor") print_pared() pared(logo_depth_mono);
else if (part == "logo_marino") print_pared() logo_svg("marino");
else if (part == "logo_azul") print_pared() logo_svg("azul");
else if (part == "logo_gris") print_pared() logo_svg("gris");
else if (part == "logo_marino_montado") logo_svg("marino");
else if (part == "check_pared_vs_ghosts") intersection() { pared(); ghost_all(); }
else if (part == "echo_oled_view") {
    c = oled_view_center();
    echo("dist", pico_x() - oled_thick - wall);
    echo("win_inner", oled_win_inner());
    echo("active", [c[0] - oled_active[0] / 2, c[1] - oled_active[1] / 2, c[0] + oled_active[0] / 2, c[1] + oled_active[1] / 2]);
    dot();
}
else if (part == "logo_gris_montado") logo_svg("gris");
else if (part == "logo_todo_montado") logo_svg("todo");
else if (part == "check_window_vs_columns") intersection() { pico_columns(); scale([20, 1, 1]) oled_window(); }
else if (part == "check_guide_vs_window") intersection() { rod_guide(); scale([20, 1, 1]) oled_window(); }
else if (part == "check_columns_short") intersection() { pico_columns(0.2); ghost_pico_pcb(); }
else if (part == "check_columns_touch") intersection() { pico_columns(-0.2); ghost_pico_pcb(); }
else if (part == "check_logo_overlap") linear_extrude(1) union() {
    intersection() { logo_2d("marino"); logo_2d("azul"); }
    intersection() { logo_2d("marino"); logo_2d("gris"); }
    intersection() { logo_2d("azul"); logo_2d("gris"); }
}
// --- push rod ---
else if (part == "pulsador") print_rod() pulsador();
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
else if (part == "marco_pi4") print_marco() marco("pi4");
else if (part == "marco_pi5") print_marco() marco("pi5");
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
else if (part == "check_xt60_bosses") intersection() { pared(); ghost_xt60(); }
else if (part == "check_xt60_cut") intersection() { pared(); translate([-xt60_depth, 0, 0]) ghost_xt60(); }
else if (part == "check_switch_cut") intersection() { pared(); translate([-sw_depth - sw_wires, 0, 0]) ghost_switch(); }
else if (part == "check_pi_standoffs_touch") intersection() { pi_standoffs(0.2); ghost_pi_pcb(); }
else if (part == "check_base_vs_pared") intersection() { base(); pared(); }
// --- shell ---
else if (part == "tapa") print_tapa() tapa();
else if (part == "check_tapa_assembled") intersection() { tapa(); union() { base(); pared(); } }
else if (part == "check_tapa_slide") intersection() { translate([0, 0, dz]) tapa(); union() { base(); pared(); } }
else if (part == "check_tapa_vs_ghosts") intersection() { tapa(); ghost_all(); }
else if (part == "echo_vents") echo_vents();
else if (part == "montaje_sin_orejetas") { pared(); base(ears = false); tapa(); }
// --- light pipes ---
else if (part == "prueba_luz") prueba_luz();
else if (part == "pared_led") print_pared() pared(leds = true);
else if (part == "pared_led_monocolor") print_pared() pared(logo_depth_mono, true);
else if (part == "logo_marino_led") print_pared() logo_svg("marino", leds = true);
else if (part == "logo_azul_led") print_pared() logo_svg("azul", leds = true);
else if (part == "logo_gris_led") print_pared() logo_svg("gris", leds = true);
else if (part == "logo_todo_led_montado") logo_svg("todo", leds = true);
else if (part == "lp_labels_montadas") lp_labels();
else if (part == "echo_lp_holes") {
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) echo(pico_leds[i][0], [w[1], w[2], lp_hole]);
    dot();
}
else if (part == "check_lp_holes_open") intersection() {
    pared(leds = true);
    for (i = [0 : len(pico_leds) - 1]) let(w = led_world(i)) translate([-1, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d = lp_d, h = wall + 2, $fn = 24);
}
else if (part == "guias_luz") print_guias() guias_luz();
else if (part == "guias_luz_montada") guias_luz();
else if (part == "check_guias_vs_pared") intersection() { guias_luz(); pared(leds = true); }
else if (part == "check_guias_vs_ghosts") intersection() { guias_luz(); ghost_all(); }
else if (part == "check_guias_vs_pcb") intersection() { guias_luz(); ghost_pico_pcb(); }
else if (part == "check_guias_held") intersection() { translate([0.5, 0, 0]) guias_luz(); pared(leds = true); }
else if (part == "check_guias_stops_at_the_wall") intersection() { translate([-0.1, 0, 0]) guias_luz(); pared(leds = true); }
else if (part == "check_hooks_vs_ghosts") intersection() { lp_hooks(); ghost_all(); }
else if (part == "echo_lp_tips") {
    for (i = [0 : len(pico_leds) - 1]) echo(pico_leds[i][0], lp_tip_x());
    echo("column_end", pico_x() - 0.05);          // pico_columns() stop 0.05 short of the board's face
    echo("hook_air", lp_hook_air);
    dot();
}
else if (part == "echo_lp_hooks") let(L = lp_ear[2] + lp_hook_air + lp_hook_lip_h - wall) {
    echo("air", lp_hook_air); echo("lip", lp_hook_lip); echo("post_len", L);
    echo("strain_pct", 100 * 3 * lp_hook_t * lp_hook_lip / (2 * L * L));
    dot();
}
else if (part == "check_pared_led_vs_ghosts") intersection() { pared(leds = true); ghost_all(); }
else if (part == "check_labels_vs_holes") intersection() { lp_labels(1); lp_holes(1); }
else if (part == "check_labels_vs_logo_led") intersection() { lp_labels(1); logo_svg("todo", 1, true); }
else if (part == "check_labels_vs_window") intersection() { lp_labels(1); scale([20, 1, 1]) oled_window(); }
else if (part == "ghost_leds_only") ghost_leds();
else if (part == "check_led_ghost_at") let(i = search([led], pico_leds)[0], w = led_world(i))
    intersection() { ghost_leds(); translate([w[0] - 0.6, w[1] - 0.2, w[2] - 0.2]) cube([0.4, 0.4, 0.4]); }
else if (part == "check_vl_dupont_vs_vl_leds") intersection() {
    ghost_pico();
    for (i = [0 : 3]) let(w = led_world(i)) translate([w[0] - pico_gap + 1, w[1], w[2]]) rotate([0, 90, 0]) cylinder(d = lp_d, h = pico_gap - 1 - led_h - 0.01, $fn = 24);
}
else if (part == "echo_leds") {
    for (i = [0 : len(pico_leds) - 1]) echo(pico_leds[i][0], led_world(i));
    echo("lp_tip_x", lp_tip_x());
    dot();
}
// --- hardware ---
else if (part == "echo_bom") {
    for (k = ["ins_m3", "ins_m25", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_flat", "nut_m3", "m25x6", "m4x12"]) echo(k, count_kind(k));
    echo("inserts_without_screw", inserts_without_screw());
    dot();
}
else if (part == "check_screws_vs_parts") intersection() { hardware(kind); printed(); }
else assert(false, str("unknown part ", part));
