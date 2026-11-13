# r2_imu

*En castellano: [README_es.md](README_es.md)*

ROS2D2's node for the MPU6050 gyroscope and accelerometer, on the Raspberry Pi's I2C. It publishes
the turn rate and the acceleration in ROS's standard message (`sensor_msgs/Imu`), and a Madgwick
filter works out the orientation from them.

## Wiring

| MPU6050 (GY-521) | Raspberry Pi 4 |
|---|---|
| VCC | 3.3 V (pin 1). The GY-521 has a regulator and also takes 5 V (pin 2) |
| GND | GND (pin 6) |
| SDA | GPIO 2 / SDA (pin 3) |
| SCL | GPIO 3 / SCL (pin 5) |
| AD0 | Not connected (address 0x68). At 3.3 V it becomes 0x69 |

It shares the bus with the DF2301QG voice module (0x64); they do not clash.

To check that the Pi sees it:

```
i2cdetect -y 1          # 68 must show up
```

**Where to mount it:** in the body, centred and as close as possible to the foot's axis, held with
thick double-sided tape or foam so the motors' vibration does not reach it.

## Use

```
ros2 launch r2_imu imu.launch.py
```

**When it starts, R2 must stand still for 2 seconds:** the node measures what the gyroscope reads at
rest (it is never exactly 0) and takes that off from then on.

| Topic | Type | What it is |
|---|---|---|
| `/imu/data_raw` | `sensor_msgs/Imu` | Turn rate (rad/s) and acceleration (m/s²), no orientation |
| `/imu/data` | `sensor_msgs/Imu` | The same with the Madgwick filter's orientation |
| `/imu/tilt` | `std_msgs/Float32` | Degrees of tilt from the horizontal |
| `/imu/temperature` | `sensor_msgs/Temperature` | The chip's temperature, once a second |

No compass, on purpose: indoors, next to the motors and the batteries, a compass gives false
readings. The heading drifts slowly, and the lidar will correct it.

## Trying it without the sensor

`docker/imu_bench.sh` starts it with a fake MPU6050 (`docker/fakes/smbus2.py`) turning at 10 °/s, and
checks that the offset is taken off and that the filter follows the turn.
