<img src="../../media/ros2d2-logo.png" alt="ROS2D2" width="420">

# Caja ROS2 rack · Instrucciones de montaje

[English version](ASSEMBLY.md)

Segunda caja, tipo rack: la placa de la Pico, la Pi y el convertidor van de pie, en paralelo. 62 × 95 × 145 mm (0,85 L). La Pi va abajo y el convertidor arriba, para que su calor no suba hacia la Pi. Vale para la Pi 4 y la Pi 5: solo cambia el marco de la trasera. La OLED, el logo y las bahías de los sensores están en la pared principal; el XT60 y el interruptor, en la frontal fija; los USB de la Pi y un HDMI de panel, detrás. Se fija al R2 de pie o tumbada con orejas desmontables. Todo va atornillado a insertos. Antes de imprimir mide lo que indica el README.

| Montada | Por detrás |
|---|---|
| ![](assembly/img/assembled.png) | ![](assembly/img/assembled_back.png) |

**Información actualizada, STL y fuentes:** <https://github.com/BeskarCode/ROS2D2/tree/main/hardware/ros2_box_rack_v3>

## Tamaño frente al R2

<img src="assembly/img/scale_es.svg" alt="Tamaño frente al R2" width="420">

## Por dentro (sin carcasa)

![](assembly/img/interior.png)

## Despiece

![](assembly/img/exploded.png)

## Tornillería y material

### Piezas impresas

| Pieza | |
|---|---|
| `stl/wall_multicolor_bambu.3mf` | Pared principal con el logo en 4 colores (AMS: blanco, marino, azul, gris) |
| `stl/wall_monocolor.stl` | o bien: pared principal de un color, logo grabado |
| `stl/leds/wall_led_multicolor_bambu.3mf` | o bien: pared con un agujero sobre cada LED de la placa de la Pico y otro sobre el de la Pico (AMS: blanco, marino, azul, gris) |
| `stl/leds/wall_led_monocolor.stl` | o bien: la pared con LEDs de un color, logo grabado |
| `stl/no_ams/wall_led_no_ams.stl` | o bien: la pared con LEDs sin AMS, logo en hueco de 1,4 mm, con sus 3 rellenos (no_ams/inlay_navy.stl, inlay_blue.stl, inlay_grey.stl) impresos aparte y pegados |
| `stl/leds/led_lenses.stl` | Lentillas de los LEDs (solo con la pared con LEDs): 13 discos de PLA translúcido (o PETG transparente), 11 y 2 de repuesto, planos sobre la cama |
| `stl/base.stl` | Base: suelo, frontal (XT60, interruptor), trasera, tabique central y rebajes de las orejas |
| `stl/shell.stl` | Tapa (techo + lateral) |
| `stl/ear.stl` | 5 orejas de fijación (4 y 1 de repuesto), de canto |
| `stl/ear_blank.stl` | 4 tapas ciegas para los rebajes sin oreja |
| `stl/frame_pi4.stl` | Marco trasero para la Pi 4 (Ethernet arriba) |
| `stl/frame_pi5.stl` | o bien: marco trasero para la Pi 5 (Ethernet abajo) |
| `stl/push_rod.stl` | Varilla del pulsador DISPLAY |

| Cant. | Pieza | Paso |
|---|---|---|
| 34× | Inserto térmico M3 (5,7 mm de largo, agujero de 4,0 mm) | 1 |
| 24× | Tornillo M3 × 8 de cabeza avellanada (ISO 10642) | 6, 7, 8 |
| 8× | Tornillo M3 × 6 de cabeza alomada (ISO 7380) | 3, 5 |
| 2× | Tornillo M3 × 6 de cabeza cilíndrica (DIN 912) | 2 |
| 2× | Tornillo M3 × 10 de cabeza alomada (ISO 7380) | 4 |
| 2× | Tuerca M3 (DIN 934) | 4 |
| 4× | Tornillo M2.5 × 6 | 3 |
| 4× | Tornillo M4 × 12 (o el que pida el soporte del R2) | 8 |
| 4× | Inserto térmico M2,5 (5 mm de largo, agujero de 3,6 mm) | 1 |

### Otro material

| Cant. | Pieza |
|---|---|
| 1 | Interruptor de balancín KCD1 (agujero de panel 19,2 × 13 mm) |
| 1 | Conector XT60E-F de panel (AMASS) |
| — | Cable de 0,5 mm² para los 5 V del borne J1 y de 1 mm² para los 24 V |
| 1 | Cable micro-USB 2.0 a USB-A con clavija recta, unos 30 cm (ver «Conectores») |
| 1 | Cable USB-C macho con hilos (5 V a la Pi), acodado 90° arriba/abajo, 15–20 cm; 3 A para la Pi 4, 5 A para la Pi 5 |
| 1 | Cable micro-HDMI macho acodado 90° a HDMI hembra de panel con 2 tornillos M3, 30 cm (mide su brida: `hdmi_*`) |

## Conexiones

![](assembly/img/wiring_es.svg)

## Conectores: hacia dónde sale cada cable

![](assembly/img/connectors_es.svg)

## 1 · Insertos térmicos

![](assembly/img/step1.png)

![](assembly/img/step1_pi.png)

**Necesitas:** 34× inserto M3, 4× inserto M2,5

Con el soldador a unos 220 °C mete los insertos rectos y a ras. Hay dos tamaños y no se cambian entre sí: 34 M3 (5,7 mm de largo, agujero de 4,0 mm) y 4 M2,5 (5 mm de largo, agujero de 3,6 mm), que son los pequeños. En el dibujo, los M3 en dorado y los M2,5 en rojo.

- **M3** · pared principal, por dentro (8): 4 en las columnas de la placa de la Pico, 2 en las pestañas de abajo y 2 en las de arriba.
- **M3** · base, por dentro (6): 2 en lo alto del tabique, 2 en el tabique para el convertidor y 2 en los bloques del suelo.
- **M3** · trasera de la base, por fuera (4): 2 del marco de la Pi y 2 del HDMI.
- **M3** · rebajes de las orejas, por fuera (16): 2 en cada uno de los 8 rebajes, 4 en la frontal y 4 en la trasera.
- **M2,5** · base (4): las 4 columnas de la Pi. Son los únicos M2,5 de la caja.

## 2 · Convertidor al tabique, arriba

![](assembly/img/step2.png)

**Necesitas:** 2× M3 × 6 cilíndrico

De pie, arriba del todo, con la base contra el tabique, las aletas hacia fuera y los cables hacia delante: van por el hueco de arriba del tabique al lado de la Pico. Así su calor sube y sale por el techo sin pasar por la Pi. Comprueba antes con el calibre sus agujeros (`conv_holes`).

## 3 · Raspberry Pi, marco y HDMI

![](assembly/img/step3.png)

**Necesitas:** 4× M2.5 × 6, 4× M3 × 6

Pi 4 o Pi 5 sobre sus 4 columnas, abajo, con los USB y el Ethernet en la ventana de la trasera y el USB-C abajo. Pincha el USB-C acodado (5 V del convertidor, bajando por delante de la Pi) y el micro-HDMI acodado en el HDMI 0; ese cable pasa bajo la Pi por el hueco de abajo del tabique. Atornilla desde fuera el marco de tu Pi (`frame_pi4` o `frame_pi5`) y el conector HDMI de panel.

## 4 · XT60 e interruptor en la frontal

![](assembly/img/step4.png)

**Necesitas:** 2× M3 × 10, 2× tuerca M3

En la frontal estrecha, que es parte de la base, en el lado de la Pi: el XT60 macho, justo encima de la Pi, desde dentro, con su frontal asomando por el hueco y la brida contra la frontal. Pon los 2 tornillos M3 desde fuera, por los agujeros pasantes y la brida, hasta las tuercas de detrás. Arriba del todo, el interruptor entra a presión desde fuera. Suelda y aísla antes sus cables: detrás hay poco fondo y se doblan nada más salir.

## 5 · Varilla y placa de la Pico

![](assembly/img/step5.png)

**Necesitas:** 4× M3 × 6

Con la pared con LEDs, mete desde fuera una lentilla en cada uno de los 11 agujeros (el de arriba, junto al USB, es el LED de la propia Pico y no lleva tubo), el tetón dentro, hasta que quede a ras; si alguna baila, una gota de pegamento. Mete la varilla desde dentro por su guía. Antes de atornillar, presenta la placa sin tornillos sobre las 4 columnas, componentes hacia la pared: debe asentar en las cuatro sin balancearse; si se balancea, algún tubo toca su LED: lija la punta. Luego atorníllala. Si algún día usas J4 (EXP), su cable rodea el tubo PWR. Aprieta los 5 V en el borne J1 y pincha el micro-USB recto en la Pico: sube recto y se dobla bajo el techo hacia la trasera. Los sensores se conectan después, desde fuera, por las bahías de la cara.

## 6 · Pared principal a la base

![](assembly/img/step6.png)

**Necesitas:** 2× M3 × 8 avellanado

Los 24 V (XT60 → interruptor → convertidor) se quedan en el lado de la Pi, junto a la frontal; los 5 V al borne J1 cruzan por el hueco de arriba del tabique y por encima de la placa. Atornilla la pared desde debajo del suelo.

## 7 · Tapa

![](assembly/img/step7.png)

**Necesitas:** 6× M3 × 8 avellanado

Es el techo y el lateral: la frontal se queda con la base. Bájala desde arriba y pon los 4 tornillos del techo y los 2 del lateral. El aire entra por las rejillas de abajo (frontal y lateral, junto a la Pi) y sale por las de arriba y el techo.

## 8 · USB, orejas y fijación al R2

![](assembly/img/step8.png)

**Necesitas:** 16× M3 × 8 avellanado, 4× M4 × 12

Saca el micro-USB por la muesca de la trasera, bájalo por fuera y enchufa su USB-A en un USB de la Pi: es el conector que se ve fuera de la caja en el dibujo (no está suelto). Por él la Pi recibe los sensores y flashea el firmware de la Pico. Elige cómo va la caja: de pie, con las 4 orejas en los rebajes junto al suelo, o tumbada sobre el lateral de la tapa, con las 4 en los rebajes junto a ese lateral. Cada oreja va a ras en su rebaje con 2 M3 × 8 avellanados; en los otros 4 rebajes, una tapa ciega con sus 2 tornillos. Luego atornilla la caja al R2 por las 4 lengüetas.
