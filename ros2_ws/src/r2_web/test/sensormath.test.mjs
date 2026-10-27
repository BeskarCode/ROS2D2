// node --test ros2_ws/src/r2_web/test/
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  toMap, fromMap, toThree, sideText, inRobot, sees, coverage, defaultName, uniqueName,
} from '../www/sensormath.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);
const tof = (o) => ({ type: 'vl53l0x', x: 0.23, y: 0, z: 0.25, yaw_deg: 0, pitch_deg: 0, fov_deg: 25, range_max: 1.2, ...o });
const sonar = (o) => ({ type: 'hcsr04', x: 0.23, y: 0, z: 0.30, yaw_deg: 0, pitch_deg: 0, fov_deg: 30, range_max: 3.0, ...o });
const lidar = (o) => ({ type: 'rplidar_c1', x: 0.17, y: 0, z: 0.11, yaw_deg: 0, pitch_deg: 0, fov_deg: 200, range_max: 12, ...o });

test('left in ROS is left on the map, front is up', () => {
  const [sx, sy] = toMap(0.2, 0.07);
  near(sx, -0.07); near(sy, -0.2);
  const p = fromMap(sx, sy);
  near(p.x, 0.2); near(p.y, 0.07);
});

test('ROS to three.js: X left, Y up, Z forward', () => {
  assert.deepEqual(toThree(0.2, 0.07, 0.25), [0.07, 0.25, 0.2]);
});

test('directions in words, never signs', () => {
  assert.equal(sideText(30), '30° left');
  assert.equal(sideText(-30), '30° right');
  assert.equal(sideText(0), 'ahead');
  assert.equal(sideText(180), 'behind');
  assert.equal(sideText(-180), 'behind');
});

test('the droid outline', () => {
  assert.equal(inRobot(0, 0), true);
  assert.equal(inRobot(0.5, 0), false);
  assert.equal(inRobot(-0.04, 0.30), true);    // left foot
});

test('a ToF sees ahead within its cone only', () => {
  assert.notEqual(sees(tof(), 0.6, 0), null);
  near(sees(tof(), 0.6, 0), 0.37);
  assert.equal(sees(tof(), 0.6, 0.4), null);
});

test('yaw + is left', () => {
  assert.notEqual(sees(tof({ yaw_deg: 45 }), 0.6, 0.37), null);
  assert.equal(sees(tof({ yaw_deg: 45 }), 0.6, -0.37), null);
});

test('the lidar does not see behind the droid', () => {
  assert.equal(sees(lidar(), -0.6, 0), null);
  assert.notEqual(sees(lidar(), 1.0, 0), null);
});

test('the body hides what is behind it', () => {
  // a sonar on the left side looking right, across the body
  assert.equal(sees(sonar({ x: 0, y: 0.25, yaw_deg: -90 }), 0, -0.6), null);
});

test('a low box passes under a high beam close up, not far away', () => {
  assert.equal(sees(sonar(), 0.53, 0, 0, 0.10), null);
  assert.notEqual(sees(sonar(), 1.73, 0, 0, 0.10), null);
});

test('a ToF tilted at the floor reaches the floor, not its full range', () => {
  assert.equal(sees(tof({ pitch_deg: 55, z: 0.28 }), 1.0, 0), null);
  assert.notEqual(sees(tof({ pitch_deg: 55, z: 0.28 }), 0.40, 0), null);
});

test('no sensors, nothing covered', () => {
  const c = coverage([]);
  assert.equal(c.near, 0); assert.equal(c.far, 0);
  assert.ok(c.gaps.length > 0);
  assert.deepEqual(c.blind, [[-180, 180]]);
});

test('sensors not found do not count', () => {
  assert.equal(coverage([lidar({ found: false })]).far, 0);
  assert.ok(coverage([lidar()]).far > 0.3);
});

test('default names: type_site from where it points', () => {
  const none = new Set();
  assert.equal(defaultName(tof({ x: 0.22, y: 0.07, yaw_deg: 30 }), none), 'tof_front_left');
  assert.equal(defaultName(tof({ yaw_deg: 0 }), none), 'tof_front');
  assert.equal(defaultName(tof({ x: 0.2, y: -0.11, yaw_deg: -15 }), none), 'tof_front_right');
  assert.equal(defaultName(sonar({ x: -0.23, yaw_deg: 180 }), none), 'sonar_rear');
  assert.equal(defaultName(sonar({ x: 0, y: 0.25, yaw_deg: 90 }), none), 'sonar_left');
  assert.equal(defaultName(tof({ pitch_deg: 55 }), none), 'tof_floor');
  assert.equal(defaultName(lidar(), none), 'lidar');
  assert.equal(defaultName(tof({ x: 0.22, y: 0.07, yaw_deg: 30 }), new Set(['tof_front_left'])), 'tof_front_left_2');
});

test('names typed by hand must be valid and unique', () => {
  assert.equal(uniqueName('tof_a', new Set(['tof_a'])), null);
  assert.equal(uniqueName('', new Set()), null);
  assert.equal(uniqueName('Bad', new Set()), null);
  assert.equal(uniqueName(' tof_b ', new Set()), 'tof_b');
});

test('the Pico pins offered leave out the I2C and the board\'s own', async () => {
  const { PICO_GPIO } = await import('../www/sensormath.js');
  for (const g of [16, 17, 23, 24, 25]) assert.ok(!PICO_GPIO.includes(g), `GP${g} offered`);
  for (const g of [0, 15, 18, 22, 26, 28]) assert.ok(PICO_GPIO.includes(g), `GP${g} missing`);
  assert.equal(PICO_GPIO.length, 24);
});
