# ROS2 box (mini tower)

*En castellano: [README_es.md](README_es.md)*

A printable box for R2's ROS 2 system: Raspberry Pi 4, the Pico board, a 24 → 5 V converter, an
XT60E-F connector and a main switch. It looks like a small standing PC. The OLED and the ROS2D2 logo
in colour go on the front. The Pi's USB/Ethernet, the XT60, the switch and the exit for the sensor
cables go at the back. It has vents on the roof and the sides.

Outside size: **107 × 133 × 125 mm** (width × depth × height), plus the 4 lugs that fix it to R2.

![Assembly](montaje/img/montada.png)

**Step-by-step assembly instructions, with an exploded view and the list of screws:**
[ASSEMBLY.md](ASSEMBLY.md) · [PDF](montaje/ASSEMBLY.pdf) — En castellano: [MONTAJE.md](MONTAJE.md) · [PDF](montaje/MONTAJE.pdf)

## Parts

| STL | What it is | How to print |
|---|---|---|
| `stl/frontal_multicolor.3mf` | front + black logo + blue logo (one object, 3 parts) | **visible face on the bed**; in Bambu Studio give white to `frontal`, black to `logo_negro` and blue to `logo_azul` |
| `stl/frontal.stl`, `stl/logo_negro.stl`, `stl/logo_azul.stl` | the same, separately | if you import the 3 STLs at once, answer **Yes** to "load as a single object with several parts?" |
| `stl/frontal_monocolor.stl` | **single-colour** front (no AMS): the logo is engraved 1 mm deep | visible face on the bed |
| `stl/pulsador.stl` | rod that presses the Pico board's DISPLAY button (SW1) from the front | standing, on its flat end |
| `stl/base.stl` | floor, back, Pi holder, converter posts and lugs | floor on the bed |
| `stl/carcasa.stl` | roof + sides (a U) with the vents | roof on the bed |

PETG recommended (the Pi and the converter get warm), 0.2 mm layers, 0.4 nozzle. No part needs
supports.

## Hardware

| Qty | What | Where |
|---|---|---|
| 14 | M3 × 5.7 heat-set insert (outside Ø ~4 mm) | 4 columns of the Pico board, 2 lower tabs and 1 upper tab of the front, 1 upper tab of the back, 4 floor blocks for the shell, 2 converter posts |
| 4 | M3 × 6, button head | Pico board → front columns |
| 2 | M3 × 8, countersunk | from under the floor → the front's lower tabs (an M3 × 10 bottoms out) |
| 4 | M3 × 8, countersunk | sides of the shell → floor blocks |
| 2 | M3 × 8, countersunk | roof of the shell → upper tabs of the front and the back |
| 2 | M3 × 8 | converter ears → floor posts |
| 2 | M3 × 10, countersunk + nut | XT60E-F (from outside; the countersink is in the flange, the wall has a plain hole) |
| 4 | M2.5 (length: the fan holder + 5 mm) | Pi → holder columns (thread into the plastic, 2.2 mm hole) |
| 4 | M4 | base lugs → R2 (4.3 mm hole) |
| 1 | KCD1 rocker switch (19.2 × 13 mm panel hole; the wall thins to 2 mm round it for its clips) | back |
| 1 | micro-USB **90° angled** to USB-A cable, ~40 cm | Pico → Pi **outside**: it leaves through the sensor slot and goes into one of the Pi's USB ports at the back |
| 1 | strip grommet or cable gland | slot for the sensor cables (35 × 10 mm) |

## Assembly

1. Fit all the heat-set inserts.
2. **Base:** screw the converter to its posts. Fit the XT60E-F and the switch on the back and
   solder/crimp: XT60 → switch → converter input.
3. **Pi:** put it next to the holder a few millimetres forward and slide it back until the
   USB/Ethernet ports sit flush in their cut-outs in the back (USB-C edge on top). Screw it to the
   columns and plug the power USB-C from the 5 V output.
4. **Pico board, with the front still loose:** first push the button rod in from the inside through
   its guide (the tip comes out of the front; the collar keeps it in). Then screw the board to the
   front's 4 columns (parts facing the front; the OLED sits behind its window). Now, while you can
   reach it, tighten the 5 V wire in terminal **J1** (leave it long enough to reach the converter),
   plug the angled micro-USB into the Pico and connect the sensors.
5. **Front to the base:** 2 screws from under the floor. Run the sensor cables and the micro-USB
   along the channels at the sides of the board to the slot at the back. Take the micro-USB out
   through the slot and plug it, outside, into one of the Pi's USB ports.
6. **Shell:** lower it from above and fit the 4 screws on the sides and the 2 on the roof.

Notes:

- The Pico board's USB-C **J5** cannot be used inside the box (there are ~11 mm to the side); inside,
  the board is powered through terminal J1.
- The M4 lugs sit 6 mm from the wall: use an Allen key or a long-shaft screwdriver.
- To take the front off, unscrew the box from R2 first (its screws go under the floor).

## Before printing: check these measurements

They are in `params.scad`; change the value and generate again.

- `xt60_hole_pitch` (25.4): distance between the 2 holes of the XT60E-F flange. The datasheet does
  not give it and it was measured on the drawing. **Measure it with a caliper**, and also the size of
  the body that goes through the wall (`xt60_body`, 9.5 × 17).
- `sw_cut` (19.2 × 13): the switch's panel hole (not the bezel, which is 21 × 15). Measure it.
- `conv_holes`: position of the converter's 2 holes from its front-left corner. They are assumed;
  **measure them** before printing the base.
- `pi_fan_clear` (25): height of the Pi's fan above the board.
- `pi_usbc_clear` (30): room above the Pi's USB-C (it can be less with an angled USB-C).
- The OLED window shows the whole display from about 20° to the right, 12° to the left (that side
  makes room for the button rod's guide) and 15° up and down. If your module's visible area is off
  centre, adjust `oled_view`.
- `sw1_h` (5): height of the DISPLAY button above the board. The rod sits 0.3 mm above it at rest and
  presses it with ~1.3 mm of travel; if your button is taller or shorter, change this value and
  generate `pulsador.stl` again.
- Print **only the front** first and try the Pico board, the OLED window and the sensors' Dupont
  connectors.

## Generating the files

Needs OpenSCAD 2021.01 (`C:\Program Files\OpenSCAD\openscad.com` or the `OPENSCAD` variable) and
Python 3 with Pillow and numpy.

```bash
python -I hardware/caja_ros2/logo/gen_logo.py      # logo PNG -> logo/logo_negro.svg, logo/logo_azul.svg
python -I hardware/caja_ros2/build.py              # stl/, 3MF and renders/
python -I hardware/caja_ros2/build_docs.py         # assembly guide: images, MONTAJE.md, ASSEMBLY.md and PDF
python -m pytest hardware/caja_ros2/tests          # sizes, clashes and alignments (~40 min the 1st time)
```

`gen_logo.py` reads `ROS2D2/docs/logo-horizontal.png`. The generated SVGs are already in `logo/`.

The tests model the Pi, the Pico board, the converter, the XT60 and the switch as "ghosts", each with
the room its connectors and cables need (the sensors' Dupont, the side channels, the micro-USB, the
USB-C...). They check that no printed part touches them, that the Pi's ports come out at the back,
that the window matches the OLED, that the shell slides in from above and that every part lies flat
on the bed.
