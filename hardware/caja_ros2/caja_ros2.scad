// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (mini torre). Pick what to render with part:
//   openscad -o frontal.stl -D 'part="frontal"' caja_ros2.scad
// Parts: montaje, frontal, logo_marino, logo_azul, logo_gris, base, carcasa (print orientation);
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <frontal.scad>
include <base.scad>
include <carcasa.scad>
include <fasteners.scad>

part = "montaje";
ga = "pico";  gb = "pi";        // check_ghost_pair
dz = 0;                         // check_shell_slide
press = 0;                      // check_rod_*
kind = "all";                   // check_screws_vs_parts

module echo_layout() {
    echo("W", W); echo("D", D); echo("H", H); echo("wall", wall);
    echo("pico_x0", pico_x0()); echo("pico_ztop", pico_ztop());
    echo("oled_view_center", oled_view_center());
    echo("pi_port_face", pi_y0() + pi_l + pi_port_out);
    cube(0.01);
}

module echo_oled_view() {
    c = oled_view_center();
    echo("dist", pico_y() - oled_thick - wall);
    echo("win_inner", oled_win_inner());
    echo("active", [c[0] - oled_active[0] / 2, c[1] - oled_active[1] / 2, c[0] + oled_active[0] / 2, c[1] + oled_active[1] / 2]);
    cube(0.01);
}

module echo_back() {
    echo("sw_cut", sw_cut); echo("xt60_hole_pitch", xt60_hole_pitch);
    echo("xt60_body", xt60_body); echo("m3_clear", m3_clear);
    cube(0.01);
}

module back_tab_wedge() {      // the 45 deg zone under the back top tab, 0.1 mm inside
    t = top_tab; y = top_tab_y()[1]; zb = H - wall - t[2];
    translate([W / 2 - t[0] / 2 + 0.1, y - t[1] / 2, zb]) hull() {
        translate([0, 0.2, -0.11]) cube([t[0] - 0.2, t[1] - 0.2, 0.01]);
        translate([0, t[1] - 0.11, -t[1] + 0.3]) cube([t[0] - 0.2, 0.01, 0.01]);
    }
}

module echo_frontal() {
    echo("col_d", col_d);
    echo("W", W);
    echo("oled_win_center", oled_win_center()); echo("oled_win_top", oled_win_top());
    echo("oled_view_center", oled_view_center());
    cube(0.01);
}

module pico_pcb() { translate([pico_x0(), pico_y(), pico_ztop() - pico_h]) cube([pico_w, pcb_t, pico_h]); }

gap = 0;                        // check_selftest
if (part == "check_selftest") intersection() { cube(10); translate([10 + gap, 0, 0]) cube(10); }
else if (part == "check_selftest_two_touches") intersection() {
    union() { cube(10); translate([0, 0, 20]) cube(10); }
    union() { translate([10, 0, 0]) cube(10); translate([0, 10, 20]) cube(10); }
}
else if (part == "ghosts") ghost_all();
else if (part == "check_ghost_pair") intersection() { ghost(ga); ghost(gb); }
else if (part == "echo_layout") echo_layout();
// --- front ---
else if (part == "frontal") print_front() frontal();
else if (part == "frontal_monocolor") print_front() frontal(logo_depth_mono);
else if (part == "check_mono_logo_cavity") intersection() { frontal(logo_depth_mono); logo_svg("todo", logo_depth_mono - 0.01); }
else if (part == "check_mono_logo_floor") intersection() { frontal(logo_depth_mono); translate([0, logo_depth_mono, 0]) logo_svg("todo", 0.3); }
else if (part == "logo_marino") print_front() frontal_logo("marino");
else if (part == "logo_azul") print_front() frontal_logo("azul");
else if (part == "logo_gris") print_front() frontal_logo("gris");
else if (part == "logo_marino_montado") frontal_logo("marino");
else if (part == "check_frontal_vs_ghosts") intersection() { frontal(); ghost_all(); }
else if (part == "check_logo_overlap") linear_extrude(1) union() {
    intersection() { logo_2d("marino"); logo_2d("azul"); }
    intersection() { logo_2d("marino"); logo_2d("gris"); }
    intersection() { logo_2d("azul"); logo_2d("gris"); }
}
else if (part == "check_columns_short") intersection() { pico_columns(0.2); pico_pcb(); }
else if (part == "check_columns_touch") intersection() { pico_columns(-0.2); pico_pcb(); }
else if (part == "echo_frontal") echo_frontal();
else if (part == "echo_oled_view") echo_oled_view();
else if (part == "check_window_vs_columns") intersection() {
    pico_columns();
    scale([1, 20, 1]) oled_window();     // the real cut-out, stretched back through the columns
}
else if (part == "echo_back") echo_back();
// --- hardware (BOM) ---
else if (part == "echo_bom") {
    for (k = ["ins_m3", "m3x8_flat", "m3x6_pan", "m3x6_cyl", "m3x10_flat", "nut_m3", "m25x6", "m4x12"])
        echo(k, count_kind(k));
    echo("inserts_without_screw", inserts_without_screw());
    cube(0.01);
}
else if (part == "check_screws_vs_parts") intersection() {
    hardware(kind);
    union() { frontal(); base(); carcasa(); }
}
// --- push rod ---
else if (part == "pulsador") print_rod() pulsador();
else if (part == "echo_pulsador") {
    echo("flange_d", rod_flange[0]); echo("bore_d", rod_bore); echo("tip_y", -rod_proud);
    cube(0.01);
}
else if (part == "check_rod_vs_ghosts") intersection() { pulsador(); ghost_all(); }
else if (part == "check_rod_vs_front") intersection() { pulsador(press); frontal(); }
else if (part == "check_rod_on_button") intersection() {
    pulsador(press);
    s = sw1_world(); translate([s[0] - 3, pico_y() - sw1_h, s[2] - 3]) cube([6, sw1_h, 6]);
}
else if (part == "check_guide_vs_window") intersection() { rod_guide(); scale([1, 20, 1]) oled_window(); }
else if (part == "check_back_tab_supported") difference() { back_tab_wedge(); base(); }
else if (part == "check_conv_insert_floor") intersection() { conv_insert_holes(); translate([-50, -50, -1]) cube([300, 300, 2.5]); }
else if (part == "check_right_vents_open") intersection() { base(); right_low_vents(); }
// --- base ---
else if (part == "base" || part == "base_montada") base();
else if (part == "check_base_vs_ghosts") intersection() { base(); ghost_all(); }
else if (part == "check_ports_clear") intersection() { base(); pi_ports(10); }
else if (part == "check_back_cut") intersection() {
    base();
    if (ga == "xt60") translate([0, xt60_depth, 0]) ghost_xt60();
    else translate([0, sw_depth + sw_wires, 0]) ghost_switch();
}
else if (part == "check_base_vs_frontal") intersection() { base(); frontal(); }
else if (part == "check_pi_standoffs_touch") intersection() { pi_bracket(0.2); ghost_pi_pcb(); }
// --- shell ---
else if (part == "carcasa") print_shell() carcasa();
else if (part == "check_shell_assembled") intersection() { carcasa(); union() { base(); frontal(); } }
else if (part == "check_shell_slide") intersection() { translate([0, 0, dz]) carcasa(); union() { base(); frontal(); } }
else if (part == "check_shell_vs_ghosts") intersection() { carcasa(); ghost_all(); }
else if (part == "check_top_screws_hit_tabs") intersection() {
    for (y = top_tab_y()) translate([W / 2, y, H - wall - 6]) cylinder(d = 6, h = 6, $fn = 24);
    union() { base(); frontal(); }
}
else if (part == "echo_vents") echo_vents();
else if (part == "montaje_sin_orejetas") { frontal(); base(ears = false); carcasa(); }
else if (part == "carcasa_montada") carcasa();
else if (part == "vista_frontal") {
    color("white") frontal();
    color([0.05, 0.13, 0.25]) frontal_logo("marino");
    color([0.25, 0.45, 0.75]) frontal_logo("azul");
    color([0.45, 0.47, 0.5]) frontal_logo("gris");
}
else if (part == "montaje") {
    color("white") frontal();
    color("lightgray") base();
    color("gray", 0.5) carcasa();
    color([0.05, 0.13, 0.25]) frontal_logo("marino");
    color([0.25, 0.45, 0.75]) frontal_logo("azul");
    color([0.45, 0.47, 0.5]) frontal_logo("gris");
    color("orange") pulsador();
    %ghost_all();
}
else assert(false, str("unknown part ", part));
