# r2_imu_bno085

*In English: [README.md](README.md)*

Nodo de la IMU **Adafruit BNO085** (ref. 4754) del ROS2D2, en modo **UART-RVC**: el propio chip
junta el giroscopio y el acelerómetro y manda la orientación ya calculada 100 veces por segundo
por un solo cable. Publica lo mismo que [`r2_imu`](../r2_imu) (el del MPU6050), así que a quien use
`/imu/data` le da igual qué IMU lleve R2.

Datos del modo UART-RVC sacados de la hoja de datos de CEVA (BNO08X, 1000-3927 v1.17, apartado 1.2.5):
115200 baudios, 8N1, 100 tramas por segundo de 19 bytes. El rumbo cuenta **desde que se enciende
el chip** y en este modo no se usa la brújula (no se calibra el magnetómetro), lo que nos viene
bien: dentro de R2 los motores y las baterías la engañarían.

## Conexión

| BNO085 (Adafruit 4754) | Raspberry Pi 4 |
|---|---|
| VIN | 3,3 V (pin 1) |
| GND | GND (pin 9) |
| SDA (en modo RVC es su **TX**) | GPIO 5, RX del `uart3` (pin 29) |
| P0 | 3,3 V (pin 17): elige el modo UART-RVC (P1 se queda a GND, como viene) |

El modo se lee al arrancar el chip: si cambias P0, quita y vuelve a dar corriente.

En la Pi, activar el `uart3` (deja libre el UART de los pines 8 y 10, que tiene la consola de Linux):

```
# /boot/firmware/config.txt
dtoverlay=uart3
```

Reiniciar y mirar qué nombre le da: `ls /dev/ttyAMA*` (en `config/imu.yaml` pone `/dev/ttyAMA3`).
El usuario tiene que estar en el grupo `dialout`.

**Dónde montarlo:** en el cuerpo, plano, centrado y lo más cerca posible del eje del foot, con
la flecha X mirando hacia delante. Sujeto con cinta de doble cara gruesa o espuma para que no le
llegue la vibración de los motores.

## Uso

```
ros2 launch r2_imu_bno085 imu.launch.py
```

| Topic | Tipo | Qué es |
|---|---|---|
| `/imu/data` | `sensor_msgs/Imu` | Orientación (del chip), velocidad de giro y aceleración (m/s²) |
| `/imu/tilt` | `std_msgs/Float32` | Grados de inclinación respecto a la horizontal |

- El modo RVC no manda la velocidad de giro: el nodo la calcula con la diferencia entre dos
  tramas seguidas (el tiempo sale del contador de tramas, no de cuándo llegan).
- `zero_yaw`: el rumbo vale 0 hacia donde mira R2 cuando arranca el nodo.
- `invert_yaw`: si al girar R2 a la izquierda el rumbo baja, ponlo a `true`.
- Si no llegan tramas o llegan con el checksum mal, el nodo lo avisa en el log (P0, cable o baudios).

## Pendiente de probar con la placa

- El nombre del puerto del `uart3` en Ubuntu.
- El sentido del rumbo (`invert_yaw`) y que no salte al acercarlo a los motores del foot.
- Meterlo en el filtro (robot_localization) junto con la odometría del lidar (`rf2o`).

## Tests

```
cd ros2_ws/src/r2_imu_bno085 && python -m pytest test
```

Incluyen la trama de ejemplo de la hoja de datos de CEVA.
