// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The swappable back frame: the base has one window for the jacks of both Pis; this frame fills it and
// leaves holes for the Pi that goes in (Ethernet and USB swap sides between the Pi 4 and the Pi 5).
// A plug the thickness of the back, a flange outside, 2 M3 screws into inserts in the back.
include <params.scad>

port_m = 0.5;                      // holes: jack + this all round

module marco(model = "pi4") {
    w = marco_win(); s = marco_screws(); f = marco_fit;
    difference() {
        union() {
            translate([w[0] + f, D - wall, w[1] + f]) cube([w[2] - w[0] - 2 * f, wall + 0.01, w[3] - w[1] - 2 * f]);   // plug
            hull() {                                                                                                  // flange
                translate([w[0] - marco_lip, D, w[1] - marco_lip]) cube([w[2] - w[0] + 2 * marco_lip, marco_t, w[3] - w[1] + 2 * marco_lip]);
                for (p = s) translate([p[0], D, p[1]]) rotate([-90, 0, 0]) cylinder(d = 9, h = marco_t, $fn = 40);
            }
        }
        pi_ports(10, model, port_m);
        for (p = s) translate([p[0], D - 1, p[1]]) rotate([-90, 0, 0]) cylinder(d = m3_clear, h = marco_t + 2 + wall, $fn = 24);
    }
}

// print orientation: flange's outer face on the bed
module print_marco() { translate([0, 0, D + marco_t]) rotate([-90, 0, 0]) children(); }
