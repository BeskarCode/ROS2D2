// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (mini torre). Pick what to render with part:
//   openscad -o frontal.stl -D 'part="frontal"' caja_ros2.scad
// Parts: montaje, frontal, logo_negro, logo_azul, base, carcasa (print orientation);
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <frontal.scad>
include <base.scad>
include <carcasa.scad>

part = "montaje";
ga = "pico";  gb = "pi";        // check_ghost_pair
dz = 0;                         // check_shell_slide

module echo_layout() {
    echo("W", W); echo("D", D); echo("H", H); echo("wall", wall);
    echo("pico_x0", pico_x0()); echo("pico_ztop", pico_ztop());
    echo("oled_view_center", oled_view_center());
    cube(0.01);
}

module echo_frontal() {
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
else if (part == "logo_negro") print_front() frontal_logo("negro");
else if (part == "logo_azul") print_front() frontal_logo("azul");
else if (part == "logo_negro_montado") frontal_logo("negro");
else if (part == "check_frontal_vs_ghosts") intersection() { frontal(); ghost_all(); }
else if (part == "check_logo_overlap") linear_extrude(1) intersection() { logo_2d("negro"); logo_2d("azul"); }
else if (part == "check_columns_short") intersection() { pico_columns(0.2); pico_pcb(); }
else if (part == "check_columns_touch") intersection() { pico_columns(-0.2); pico_pcb(); }
else if (part == "echo_frontal") echo_frontal();
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
    color("black") frontal_logo("negro");
    color("royalblue") frontal_logo("azul");
}
else if (part == "montaje") {
    color("white") frontal();
    color("lightgray") base();
    color("gray", 0.5) carcasa();
    color("black") frontal_logo("negro");
    color("royalblue") frontal_logo("azul");
    %ghost_all();
}
else assert(false, str("unknown part ", part));
