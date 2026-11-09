// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (mini torre). Pick what to render with part:
//   openscad -o frontal.stl -D 'part="frontal"' caja_ros2.scad
// Parts: montaje, frontal, logo_negro, logo_azul, base, carcasa (print orientation);
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>
include <frontal.scad>

part = "montaje";
ga = "pico";  gb = "pi";        // check_ghost_pair

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

if (part == "ghosts") ghost_all();
else if (part == "check_ghost_pair") intersection() { ghost(ga); ghost(gb); }
else if (part == "echo_layout") echo_layout();
// --- front ---
else if (part == "frontal") print_front() frontal();
else if (part == "logo_negro") print_front() frontal_logo("negro");
else if (part == "logo_azul") print_front() frontal_logo("azul");
else if (part == "logo_negro_montado") frontal_logo("negro");
else if (part == "check_frontal_vs_ghosts") intersection() { frontal(); ghost_all(); }
else if (part == "check_logo_overlap") linear_extrude(1) intersection() { logo_2d("negro"); logo_2d("azul"); }
else if (part == "check_columns_short") intersection() { pico_columns(0.2); pico_pcb(); }
else if (part == "check_columns_touch") intersection() { pico_columns(-0.2); pico_pcb(); }
else if (part == "echo_frontal") echo_frontal();
else if (part == "montaje") {
    color("white") frontal();
    color("black") frontal_logo("negro");
    color("royalblue") frontal_logo("azul");
    %ghost_all();
}
else assert(false, str("unknown part ", part));
