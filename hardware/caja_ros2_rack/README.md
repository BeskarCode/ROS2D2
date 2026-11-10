# Caja ROS2 · opción C "rack blade"

Segunda caja para el mismo sistema ROS 2 del R2 (Raspberry Pi 4, placa de la Pico, convertidor
24 → 5 V, XT60E-F e interruptor), más pequeña que la mini torre de [`../caja_ros2`](../caja_ros2):
las placas van **de pie, en paralelo, como cuchillas de un rack**.

**78 × 95 × 127 mm · 0,94 L** (la mini torre: 107 × 133 × 125, 1,78 L), más 4 orejetas.

![Montada](montaje/img/montada.png)

**Instrucciones de montaje paso a paso, con despiece, lista de tornillería y plano de conexiones:**
[MONTAJE.md](MONTAJE.md) · [PDF](montaje/MONTAJE.pdf) — English: [ASSEMBLY.md](ASSEMBLY.md) · [PDF](montaje/ASSEMBLY.pdf)

## Cómo va por dentro

- **Pared principal** (el lateral grande): ventana de la OLED, logo en 4 colores, varilla del
  pulsador DISPLAY, ranura única para los cables de los sensores (arriba) y, abajo, el XT60E-F
  (girado) y el interruptor.
- **Placa de la Pico**: de pie, colgada de 4 columnas de la pared principal, con los componentes
  hacia ella (30 mm para los Dupont).
- **Tabique central**: sujeta la Pi (columnas M2.5) y el convertidor (insertos M3). Abajo tiene un
  paso para los cables de 24 V y de 5 V.
- **Raspberry Pi**: de pie, arriba, con los USB y el Ethernet a ras de la trasera y el USB-C hacia
  abajo.
- **Convertidor**: de pie, debajo de la Pi, con los cables hacia delante.
- **Tapa**: techo, lateral derecho y frontal estrecho en una pieza que baja desde arriba.

## Piezas

| STL | Qué es | Cómo imprimir |
|---|---|---|
| `stl/pared_multicolor_bambu.3mf` | pared principal + logo marino, azul y gris (4 partes con su filamento) | cara del logo sobre la cama; AMS: 1 blanco, 2 marino, 3 azul, 4 gris |
| `stl/pared_multicolor.3mf` | lo mismo, 3MF genérico para otros laminadores | |
| `stl/pared_monocolor.stl` | pared principal de un color, logo grabado 1 mm | cara del logo sobre la cama |
| `stl/base.stl` | suelo, trasera, tabique y orejetas | suelo sobre la cama |
| `stl/tapa.stl` | techo, lateral y frontal estrecho | techo sobre la cama |
| `stl/pulsador.stl` | varilla del pulsador DISPLAY | de pie |

PETG, 0,2 mm, boquilla 0,4, sin soportes.

## Antes de imprimir: comprueba estas medidas

En `params.scad` (cambia el valor y vuelve a generar):

- `conv_holes`: agujeros de las orejetas del convertidor (sacados del plano de RCNUN; comprueba con
  calibre la distancia a la punta de la orejeta).
- `xt60_hole_pitch` y `xt60_body`: XT60E-F (paso entre agujeros sin acotar en su plano).
- `sw_cut`: agujero de panel del interruptor (19,2 × 13 para un KCD1).
- `sw1_h`: altura del pulsador DISPLAY.
- `pi_fan_clear`: altura del ventilador de la Pi.

Cables: el **micro-USB acodado lateral de 30 cm** y el **USB-C acodado con hilos** (3 A) son los
mismos que en la mini torre; mira «Conectores acodados» en el manual.

## Generar los ficheros

```bash
python -I hardware/caja_ros2_rack/build.py         # stl/ y los 3MF
python -I hardware/caja_ros2_rack/build_docs.py    # imágenes, MONTAJE.md, ASSEMBLY.md y PDF
python -m pytest hardware/caja_ros2_rack/tests     # choques, encajes, tornillería, impresión
```

El logo y sus SVG se comparten con la mini torre (`../caja_ros2/logo`), escalados a 80 mm.
