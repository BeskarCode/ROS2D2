// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Caja ROS2 (mini torre). Pick what to render with part:
//   openscad -o frontal.stl -D 'part="frontal"' caja_ros2.scad
// Parts: montaje, frontal, logo_negro, logo_azul, base, carcasa (print orientation);
// ghosts, check_*, echo_* are for the tests.
include <params.scad>
include <ghosts.scad>

part = "montaje";
ga = "pico";  gb = "pi";        // check_ghost_pair

module echo_layout() {
    echo("W", W); echo("D", D); echo("H", H); echo("wall", wall);
    echo("pico_x0", pico_x0()); echo("pico_ztop", pico_ztop());
    echo("oled_view_center", oled_view_center());
    cube(0.01);
}

if (part == "ghosts") ghost_all();
else if (part == "check_ghost_pair") intersection() { ghost(ga); ghost(gb); }
else if (part == "echo_layout") echo_layout();
else if (part == "montaje") { %ghost_all(); }
else assert(false, str("unknown part ", part));
