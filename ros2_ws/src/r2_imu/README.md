# r2_imu

Nodo del giroscopio y acelerómetro MPU6050 del ROS2D2, conectado al I2C de la
Raspberry. Publica el giro y la aceleración en el mensaje estándar de ROS
(`sensor_msgs/Imu`), y un filtro Madgwick calcula a partir de ellos la orientación.

## Conexión

| MPU6050 (GY-521) | Raspberry Pi 4 |
|---|---|
| VCC | 3,3 V (pin 1). El GY-521 lleva regulador y también admite 5 V (pin 2) |
| GND | GND (pin 6) |
| SDA | GPIO 2 / SDA (pin 3) |
| SCL | GPIO 3 / SCL (pin 5) |
| AD0 | Sin conectar (dirección 0x68). A 3,3 V pasa a 0x69 |

Comparte bus con el módulo de voz DF2301QG (0x64); no chocan.

Para comprobar que la Pi lo ve:

```
i2cdetect -y 1          # debe aparecer 68
```

**Dónde montarlo:** en el cuerpo, centrado y lo más cerca posible del eje de los
pies, sujeto con cinta de doble cara gruesa o espuma para que no le llegue la
vibración de los motores.

## Uso

```
ros2 launch r2_imu imu.launch.py
```

**Al arrancar, el R2 tiene que estar quieto 2 segundos:** el nodo mide cuánto marca
el giroscopio en reposo (nunca es exactamente 0) y a partir de ahí lo descuenta.

| Topic | Tipo | Qué es |
|---|---|---|
| `/imu/data_raw` | `sensor_msgs/Imu` | Giro (rad/s) y aceleración (m/s²), sin orientación |
| `/imu/data` | `sensor_msgs/Imu` | Lo mismo con la orientación del filtro Madgwick |
| `/imu/tilt` | `std_msgs/Float32` | Grados de inclinación respecto a la horizontal |
| `/imu/temperature` | `sensor_msgs/Temperature` | Temperatura del chip, una vez por segundo |

Sin brújula a propósito: dentro de casa, junto a los motores y las baterías, una
brújula da lecturas falsas. El rumbo se desvía poco a poco y lo corregirá el lidar.

## Probarlo sin el sensor

`docker/imu_bench.sh` lo arranca con un MPU6050 falso (`docker/fakes/smbus2.py`)
que gira a 10 °/s, y comprueba que el desvío se descuenta y que el filtro sigue el giro.
