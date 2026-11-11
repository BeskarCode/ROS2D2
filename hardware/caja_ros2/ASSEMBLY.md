<img src="../../media/ros2d2-logo.png" alt="ROS2D2" width="420">

# ROS2 box · Assembly instructions

[Versión en castellano](MONTAJE.md)

Mini-tower box for the Raspberry Pi 4, the Pico board, the 24 → 5 V converter, the XT60 and the switch. Before printing, measure what the README lists (XT60, switch, converter holes, button and fan heights).

| Assembled | From the back |
|---|---|
| ![](montaje/img/montada.png) | ![](montaje/img/montada_atras.png) |

**Up-to-date guide, STL and sources:** <https://github.com/BeskarCode/ROS2D2/tree/main/hardware/caja_ros2>

## Size next to the R2

<img src="montaje/img/escala_en.svg" alt="Size next to the R2" width="420">

## Inside (no shell)

![](montaje/img/interior.png)

## Exploded view

![](montaje/img/despiece.png)

## Hardware and parts

### Printed parts

| Part | |
|---|---|
| `stl/frontal_multicolor_bambu.3mf` | Front with the logo in 4 colours (AMS: white, navy, blue, grey) |
| `stl/frontal_monocolor.stl` | or: single-colour front, engraved logo |
| `stl/base.stl` | Base: floor, back, Pi bracket |
| `stl/carcasa.stl` | U shell (roof + sides) |
| `stl/pulsador.stl` | DISPLAY push rod |

| Qty | Part | Step |
|---|---|---|
| 14× | M3 heat-set insert (5.7 mm long, 4.0 mm hole) | 1 |
| 8× | M3 × 8 countersunk screw (ISO 10642) | 6, 7 |
| 4× | M3 × 6 button head screw (ISO 7380) | 5 |
| 2× | M3 × 6 socket head cap screw (DIN 912) | 2 |
| 2× | M3 × 10 countersunk screw (ISO 10642) | 3 |
| 2× | M3 nut (DIN 934) | 3 |
| 4× | M2.5 × 6 screw (longer if the Pi's fan sits on spacers) | 4 |
| 4× | M4 × 12 screw (or what the R2's mount needs) | 8 |

### Other parts

| Qty | Part |
|---|---|
| 1 | KCD1 rocker switch (panel hole 19.2 × 13 mm) |
| 1 | XT60E-F panel connector (AMASS) |
| 1 | micro-USB 2.0 to USB-A cable, 90° side angle, 30 cm (see «Angled plugs») |
| 1 | USB-C male pigtail (5 V to the Pi), 3 A, 15–20 cm; straight or 90° angled |
| — | 0.5 mm² wire for the 5 V to terminal J1, 1 mm² for the 24 V |
| 1 | Edge grommet strip for the 35 × 10 mm slot |

## Wiring

![](montaje/img/conexiones_en.svg)

## Angled plugs: which way the cable goes

![](montaje/img/conectores_en.svg)

## 1 · Heat-set inserts

![](montaje/img/paso1.png)

**You need:** 14× M3 insert

With the soldering iron at about 220 °C, press the inserts in straight and flush: on the front, 4 in the columns, 2 in the bottom tabs and 1 in the top tab; on the base, 4 in the floor blocks, 2 in the converter bosses and 1 in the top tab.

## 2 · 24 → 5 V converter

![](montaje/img/paso2.png)

**You need:** 2× M3 × 6 socket head

Screw it onto its two bosses, wires towards the back. Check its holes (`conv_holes`) with a caliper before printing the base.

## 3 · XT60 and switch

![](montaje/img/paso3.png)

**You need:** 2× M3 × 10 countersunk, 2× M3 nut

From the outside: the XT60E-F with 2 screws and their nuts inside, and the switch snapped in. Wire the 24 V: XT60 → switch → converter input.

## 4 · Raspberry Pi

![](montaje/img/paso4.png)

**You need:** 4× M2.5 × 6

Hold it against the bracket a few mm forward and slide it back until the USB and Ethernet jacks come flush out of the back. Screw it on and plug in the 5 V USB-C from the converter.

## 5 · Push rod and Pico board

![](montaje/img/paso5.png)

**You need:** 4× M3 × 6

Slide the push rod into its guide from the inside. Screw the board onto the 4 columns, parts facing the front. With the front still loose: tighten the 5 V in terminal J1, plug the angled micro-USB into the Pico and connect the sensors.

## 6 · Front onto the base

![](montaje/img/paso6.png)

**You need:** 2× M3 × 8 countersunk

Run the sensor cables and the micro-USB along the channels beside the board to the slot in the back. Screw the front on from under the floor.

## 7 · Shell

![](montaje/img/paso7.png)

**You need:** 6× M3 × 8 countersunk

Lower it from above and fit the 4 side screws and the 2 roof screws.

## 8 · USB and onto the R2

![](montaje/img/paso8.png)

**You need:** 4× M4 × 12

Bring the micro-USB out through the slot into a Pi USB port. Screw the box to the R2 through its 4 ears (use a hex key: they are 6 mm from the wall).
