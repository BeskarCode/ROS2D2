// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 · option C, "rack blade". Pick what to render with part:
//   openscad -o pared.stl -D 'part="pared"' caja_rack.scad
// Parts (print orientation): pared, logo_marino, logo_azul, logo_gris, pared_monocolor, pulsador, base, tapa.
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <pared.scad>
include <base.scad>
include <tapa.scad>
include <fasteners.scad>

part = "pared";
ga = "pico";  gb = "pi";
dz = 0;  press = 0;  kind = "all";  gap = 0;

module dot() { cube(0.01); }
module printed() { pared(); base(); tapa(); }

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
// --- hardware ---
else if (part == "echo_bom") {
    for (k = ["ins_m3", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_flat", "nut_m3", "m25x6", "m4x12"]) echo(k, count_kind(k));
    echo("inserts_without_screw", inserts_without_screw());
    dot();
}
else if (part == "check_screws_vs_parts") intersection() { hardware(kind); printed(); }
else assert(false, str("unknown part ", part));
