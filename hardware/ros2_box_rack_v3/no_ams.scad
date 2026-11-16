// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The LED face for printers without AMS: the same face, tubes and inserts as wall_led, but the logo and the
// logo is a deep pocket (na_depth) and its fillings print apart, one colour per plate:
// navy (ROS), blue (2D2 + the 12 dots) and grey (the dots' frame). Glue them in flush.
include <params.scad>

// in the face's outside view: u = -Y (to the right seen from outside), v = Z
module na_2d(c) {
    translate([-(D / 2 + logo_w / 2), logo_zc_led - logo_h / 2]) scale(logo_w / LOGO_SVG_W) logo_2d(c);
}
module na_put(depth) multmatrix([[0, 0, -1, depth], [-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(depth) children();

module na_pockets(depth = na_depth, grow = 0) na_put(depth) offset(delta = na_fit + grow) union() for (c = logo_colours) na_2d(c);
module relleno(c) na_put(na_depth) na_2d(c);

module pared_no_ams() pared(leds = true, noams = true);
