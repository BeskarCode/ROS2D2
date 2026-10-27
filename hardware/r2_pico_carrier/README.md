# R2 Pico carrier

Placa base para la **Raspberry Pi Pico 2** que lee los sensores de distancia de R2
(firmware: `firmware/r2_pico_sensors`). Se encarga **ya montada**: tú solo pinchas la Pico
(con sus pines soldados hacia abajo) y los cables de los sensores.

![Arriba](renders/top.png)

- 80 × 72 mm, 2 capas, 4 agujeros M3 en las esquinas.
- Detrás: logo de Astromech Spain, **ROS2D2**, **by NandoMadrid**, www.astromechspain.com.
- Esquema: [`renders/schematic.pdf`](renders/schematic.pdf). Vista 3D: [`renders/3d.png`](renders/3d.png).

## Conectores

Cada conector tiene los pines **en el mismo orden que el módulo**, así que un cable Dupont
hembra-hembra recto va directo, sin cruzar nada. El pin 1 es el de la izquierda (pad cuadrado).

| Conector | Pines (izquierda → derecha) | Para |
|---|---|---|
| **VL1, VL2** (< 50 cm) | 3V3 · GND · SCL · SDA · — (GPIO1, libre) · XSHUT | VL53L0X (GY-530) con cable corto |
| **VL3, VL4** (> 50 cm) | igual | VL53L0X con cable largo: van por un repetidor I2C (PCA9517A) |
| **US1 … US5** | 5V · TRIG · ECHO · GND | HC-SR04. El divisor de ECHO (1 kΩ / 2 kΩ) ya está en la placa |
| **OLED** (hembra) | GND · VCC · SCL · SDA | Pantalla 0,96" SSD1306 I2C de 4 pines |
| **+5V / GND** (borna) | 5 V de la fuente del droide | Alimenta los HC-SR04, los LEDs y la Pico |
| **DISPLAY** | pulsador | Enciende la pantalla y pasa de sensor |

Con el `sensors.yaml` de hoy: `tof_front_left` → VL1, `tof_front` → VL2, `tof_front_right` → VL3,
`tof_floor` → VL4, `sonar_front_left` → US1, `sonar_front_right` → US2, `sonar_rear` → US3.
US4 y US5 son para los dos HC-SR04 de repuesto (GP18/19 y GP20/21).

**Regla del cable:** si el cable de un VL53L0X mide más de 50 cm, enchúfalo en VL3 o VL4. Los
HC-SR04 aguantan cables largos en cualquier US.

## Alimentación

- **Borna +5V / GND**: 5 V de la fuente del droide. Lleva fusible rearmable (750 mA) y diodo
  contra la polaridad invertida (si conectas los cables al revés no se quema nada, solo no
  funciona). El LED verde junto a la borna dice que hay 5 V.
- El **USB** de la Pico va a la Pi 4 para los datos. La Pico funciona con el USB o con la borna;
  los HC-SR04 y los LEDs **solo con la borna**.

## Pantalla y LEDs

Apagados hasta que pulsas **DISPLAY**: primera pulsación, el logo; la siguiente, el último
sensor visto; cada pulsación, el siguiente. A los 30 s sin pulsar se apaga todo. Un LED por
conector: verde mide, rojo parpadeando no responde, apagado sin configurar, azul esperando a la Pi.

## Pedirla

Hay dos paquetes, uno por fábrica. **Revisa siempre la vista previa del montaje antes de pagar.**

### JLCPCB (`jlcpcb/`)

1. jlcpcb.com → *Order now* → *Add gerber file* → `jlcpcb/gerber.zip`. Deja 2 capas, 1,6 mm.
2. Activa **PCB Assembly**, cara **Top**, tipo *Economic* si lo permite (si no, *Standard*:
   las tiras y zócalos son de agujero pasante).
3. Sube `jlcpcb/bom.csv` y `jlcpcb/cpl.csv`.
4. En la vista previa de colocación mira **la orientación** de D1-D3 (raya = cátodo), LED1-LED9,
   U1 y D4. Si alguna está girada, corrígela allí mismo.
5. Comprueba que las 19 líneas del BOM tienen pieza y stock. No pagues nada que no cuadre.

### PCBWay (`pcbway/`)

1. pcbway.com → *PCB Instant Quote* → *Quick-order PCB* → sube `pcbway/gerber.zip`.
2. Marca **Assembly** (Turnkey), cara Top.
3. Sube `pcbway/bom.csv` y `pcbway/centroid.csv`. El BOM lleva fabricante y referencia de
   fabricante (y, de nota, el número LCSC por si lo buscan allí).
4. PCBWay revisa el BOM a mano y te da el precio final por correo; revisa las orientaciones en su
   vista previa igual que arriba.

## Qué comprar aparte

- Pantalla OLED 0,96" **SSD1306 I2C, 4 pines** en orden **GND-VCC-SCL-SDA** (algunas traen
  VCC-GND: compruébalo antes de pincharla).
- Cables Dupont hembra-hembra.
- Tiras de pines macho 1×20 para soldar a tu Pico 2 (hacia abajo), si no las tiene.

## Rehacerla

Todo sale de `gen/parts.py` (piezas, huellas, LCSC y la red de cada pad), con el Python de KiCad 10:

```
$KPY gen/make_sch.py     # esquema (ERC limpio)
$KPY gen/make_pcb.py     # placa sin pistas: contorno, colocación, serigrafía
$KPY gen/route.py        # ruteo con Freerouting (Java 25 + freerouting-2.5.0.jar)
$KPY gen/make_fab.py     # paquetes jlcpcb/ y pcbway/
$KPY -m pytest gen       # comprobaciones (conexiones, esquema = parts.py, paquetes)
kicad-cli pcb drc --schematic-parity --severity-all r2_pico_carrier.kicad_pcb
```

`$KPY` = `C:\Users\Usuario\AppData\Local\Programs\KiCad\10.0\bin\python.exe`.
