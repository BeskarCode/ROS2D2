# ROS2 box (rack)

*En castellano: [README_es.md](README_es.md)*

The box for the R2 ROS 2 system (Raspberry Pi 4 or Pi 5, the Pico board, a 24 → 5 V
converter, an XT60E-F and a switch): the boards stand **upright, side by side, like the blades of a rack**.

**78 × 95 × 145 mm · 1.07 L**, plus 4 lugs.

Every screw goes into a **heat-set insert**, the boards' too (M2.5 for the Pi, M3 for the rest).

![Assembled](assembly/img/assembled.png)

**Step-by-step assembly instructions, with an exploded view, the list of screws and the wiring:**
[ASSEMBLY.md](ASSEMBLY.md) · [PDF](assembly/ASSEMBLY.pdf) — En castellano: [MONTAJE.md](MONTAJE.md) · [PDF](assembly/MONTAJE.pdf)

**Print guide** (which wall, frame and parts to print for each case, with a picture of each): [PRINT_GUIDE.md](print_guide/PRINT_GUIDE.md) · [PDF](print_guide/PRINT_GUIDE.pdf) — En castellano: [GUIA_IMPRESION.md](print_guide/GUIA_IMPRESION.md) · [PDF](print_guide/GUIA_IMPRESION.pdf)

## What goes where inside

- **Main wall** (the large side): the OLED window, the logo in 4 colours, the DISPLAY button rod, a
  single slot for the sensor cables (at the top) and, at the bottom, the XT60E-F (turned) and the
  switch.
- **Pico board**: upright, hanging from 4 columns of the main wall, parts facing it (30 mm for the
  Dupont connectors).
- **Middle divider**: holds the Pi (columns with M2.5 inserts) and the converter (M3 inserts). It has
  two cable passes: top front, where the converter's wires go out towards the Pico side; and bottom,
  under the Pi, for the HDMI (and the USB-C if you want to route it there).
- **Raspberry Pi 4 or Pi 5**: upright, **at the bottom**, with the USB and Ethernet in the window at
  the back and the USB-C facing down (15 mm free for angled USB-C and micro-HDMI plugs).
- **Converter**: upright, **at the top**, with 5 mm of air above the Pi and its wires facing forward.
  Its heat rises and leaves through the roof and the side's upper vent without passing the Pi; the Pi
  takes fresh air through the lower vents of the front and the side.
- **Back**: a single window for both Pis' connectors, closed with a **swappable frame** (`frame_pi4`
  or `frame_pi5`: the Pi 5 has the Ethernet and the USB the other way round). The USB openings are
  0.5 mm bigger on each side for the tabs of the connector's shell. Next to it, an **HDMI panel
  socket** wired to the Pi's HDMI 0, to plug in a monitor.
- **Lid**: roof, right side and narrow front in one piece that comes down from above.

## Parts

| STL | What it is | How to print |
|---|---|---|
| `stl/wall_multicolor_bambu.3mf` | main wall + navy, blue and grey logo (4 parts with their filament) | logo face on the bed; AMS: 1 white, 2 navy, 3 blue, 4 grey |
| `stl/wall_multicolor.3mf` | the same, generic 3MF for other slicers | |
| `stl/wall_monocolor.stl` | single-colour main wall, logo engraved 1 mm | logo face on the bed |
| `stl/base.stl` | floor, back, divider and lugs | floor on the bed |
| `stl/shell.stl` | roof, side and narrow front | roof on the bed |
| `stl/push_rod.stl` | DISPLAY button rod | standing |
| `stl/frame_pi4.stl` | back frame for the Pi 4 | outer face on the bed |
| `stl/frame_pi5.stl` | back frame for the Pi 5 | outer face on the bed |

PETG, 0.2 mm, 0.4 nozzle, no supports.

## Main wall with LEDs (optional)

![Main wall with LEDs](assembly/img/assembled_led.png)

Another version of the main wall, to see the Pico board's 10 LEDs from outside: a hole over each one
(VL1–VL4, US1–US5 and PWR) with its name beside it, and the logo lower down, between the OLED window
and the XT60. Its parts are in `stl/leds/`. Print **one** of the two walls: the one above or this
one. The other parts are the same.

| STL | What it is | How to print |
|---|---|---|
| `stl/leds/wall_led_multicolor_bambu.3mf` | wall with LEDs + logo and names in navy, blue and grey | logo face on the bed; AMS: 1 white, 2 navy, 3 blue, 4 grey |
| `stl/leds/wall_led_multicolor.3mf` | the same, generic 3MF | |
| `stl/leds/wall_led_monocolor.stl` | single-colour wall with LEDs, logo and names engraved 1 mm | logo face on the bed |
| `stl/leds/led_lenses.stl` | 12 lenses (10 and 2 spares) | **translucent PLA** (or clear PETG), discs flat on the bed |

Behind each hole a dark tube, printed with the wall, carries its LED's light outside without losing it;
it ends 0.7 mm above the LED and never touches the board. A translucent PLA lens is pressed into the
mouth of each tube, flush with the wall (if one is loose, a drop of glue). When assembling, rest the
board on its 4 columns without screws: it must sit without rocking; if it rocks, a tube touches its
LED: sand its tip.

## Main wall with LEDs without AMS (optional)

The same LED wall (same tubes, lenses and inserts) for printers without AMS: the logo and the connector
names are 1.5 mm deep pockets, and what fills them prints apart, one piece per colour. Its parts are in
`stl/no_ams/`; the lenses are `stl/leds/led_lenses.stl`.

| STL | What it is | How to print |
|---|---|---|
| `stl/no_ams/wall_led_no_ams.stl` | LED wall, logo and names as 1.5 mm pockets | white, logo face on the bed |
| `stl/no_ams/inlay_navy.stl` | "ROS" and the connector names | navy, visible face on the bed |
| `stl/no_ams/inlay_blue.stl` | "2D2" and the 12 dots | blue, visible face on the bed |
| `stl/no_ams/inlay_grey.stl` | the dots' frame | grey, visible face on the bed |

The fillings come out in place, as seen from outside but mirrored (visible face down): turn them over
and press them into their pockets. They have 0.1 mm of play per side and end flush with the wall; fix
them with a drop of cyanoacrylate glue. The names are a little bolder than in the AMS version so they
can print on their own. Print the fillings at 0.1–0.15 mm layers, no brim.

## Before printing: check these measurements

In `params.scad` (change the value and generate again):

- `conv_holes`: the holes in the converter's ears (taken from RCNUN's drawing; check with a caliper
  the distance to the tip of the ear).
- `xt60_hole_pitch` and `xt60_body`: XT60E-F (the hole pitch is not given in its drawing).
- `sw_cut`: the switch's panel hole (19.2 × 13 for a KCD1).
- `sw1_h`: height of the DISPLAY button.
- `pi_fan_clear`: height of the Pi's fan.
- `hdmi_body`, `hdmi_flange`, `hdmi_pitch`: the HDMI panel socket you buy (body, flange and distance
  between its 2 M3 screws).

Cables: the **30 cm side-angled micro-USB** and the **angled USB-C pigtail** (3 A for the Pi 4; **5 A for the Pi 5**); see "Angled connectors" in the guide. For the
monitor, an **angled male micro-HDMI → HDMI panel socket** cable, about 30 cm.

## Generating the files

```bash
python -I hardware/ros2_box_rack/build.py         # stl/ and the 3MFs
python -I hardware/ros2_box_rack/build_docs.py    # images, MONTAJE.md, ASSEMBLY.md and PDF
python -m pytest hardware/ros2_box_rack/tests     # clashes, fits, screws, printing
```

The logo and its SVGs are in `logo/`, scaled to 80 mm.
