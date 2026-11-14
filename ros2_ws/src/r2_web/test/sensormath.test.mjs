// node --test ros2_ws/src/r2_web/test/
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  toMap, fromMap, toThree, sideText, inRobot, sees, coverage, defaultName, uniqueName, freeRadius, nearestPoint, beamDefaults, connectorOf, connectorPins, freeConnector,
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
  for (const g of [0, 1, 6, 7, 8, 9, 16, 17, 22, 23, 24, 25, 26, 27, 28]) assert.ok(!PICO_GPIO.includes(g), `GP${g} offered`);
  for (const g of [2, 5, 10, 15, 18, 21]) assert.ok(PICO_GPIO.includes(g), `GP${g} missing`);
  assert.equal(PICO_GPIO.length, 14);
});

test('free circle: the nearest lidar point from the droid centre', () => {
  near(freeRadius([[1.5, 0], [0, -0.8], [-2, 2]]), 0.8);
  near(freeRadius([[0.6, 0.8]]), 1.0);                 // centre distance, not just x
});

test('free circle: points on the droid itself (body, feet) do not count', () => {
  near(freeRadius([[0.05, 0.05], [0, 0.1], [0.9, 0]]), 0.9);
});

test('free circle: no points, no circle', () => {
  assert.equal(freeRadius([]), null);
  assert.equal(freeRadius(null), null);
  assert.equal(freeRadius([[0.01, 0]]), null);          // only the droid's own reflections
});

test('nearest point: where the free circle touches, for the line to it', () => {
  assert.deepEqual(nearestPoint([[1.5, 0], [0, -0.8], [0.05, 0.05]]), { x: 0, y: -0.8, r: 0.8 });
  assert.equal(nearestPoint([]), null);
});

test('"Defaults" gives each type its own beam (the same as r2_sensors/config.py TYPES)', () => {
  assert.deepEqual(beamDefaults('vl53l0x'), { fov_deg: 25, range_min: 0.03, range_max: 1.2 });
  assert.deepEqual(beamDefaults('hcsr04'), { fov_deg: 30, range_min: 0.02, range_max: 3 });
  assert.deepEqual(beamDefaults('rplidar_c1'), { fov_deg: 200, range_min: 0.05, range_max: 12 });
});

test('the carrier board connectors: which one a sensor is on, and the first free one', () => {
  assert.equal(connectorOf({ type: 'vl53l0x', pico: { xshut: 4 } }), 'VL3');
  assert.equal(connectorOf({ type: 'hcsr04', pico: { trig: 18, echo: 19 } }), 'US4');
  assert.equal(connectorOf({ type: 'hcsr04', pico: { trig: 19, echo: 18 } }), null);     // swapped: not the board's
  assert.equal(connectorOf({ type: 'vl53l0x', pico: { xshut: 11 } }), null);             // wired straight to the Pico
  assert.equal(connectorOf({ type: 'rplidar_c1', port: '/dev/r2-lidar' }), null);
  assert.deepEqual(connectorPins('hcsr04', 'US5'), { trig: 20, echo: 21 });
  const vl = (g) => ({ type: 'vl53l0x', pico: { xshut: g } });
  assert.equal(freeConnector('vl53l0x', [vl(2), vl(4)]), 'VL2');
  assert.equal(freeConnector('vl53l0x', [vl(2), vl(3), vl(4), vl(5)]), null);
  // a pin used by something else (here a sonar wired by hand on GP10) blocks that connector
  assert.equal(freeConnector('hcsr04', [{ type: 'hcsr04', pico: { trig: 3, echo: 10 } }]), 'US2');
});

// ---------- the lidar's own settings ----------
import { lidarModes, lidarInfoText, blindSectorsBase, lidarYamlValue } from '../www/sensormath.js';

test('lidarModes falls back without info', () => {
  assert.deepEqual(lidarModes(null), ['Standard', 'DenseBoost']);
  assert.deepEqual(lidarModes({ modes: [] }), ['Standard', 'DenseBoost']);
  assert.deepEqual(lidarModes({ modes: [{ name: 'Standard' }, { name: 'Express' }] }), ['Standard', 'Express']);
});

test('lidarInfoText without info', () => {
  assert.match(lidarInfoText(null, null, null), /unknown/);
});

test('lidarInfoText with info', () => {
  const t = lidarInfoText({ model: '0x41', firmware: '1.02', hardware: 18, health: 'OK', scan_mode: 'Standard' }, 10.5, 476);
  for (const w of ['0x41', '1.02', '18', 'OK', 'Standard', '10.5', '476']) assert.ok(t.includes(w), w);
});

test('lidarInfoText says when the mode did not start', () => {
  assert.match(lidarInfoText({ model: '0x41', firmware: '1.02', hardware: 18, health: 'OK', scan_mode: null }, null, null), /did not start/);
});

test('blindSectorsBase mirrors when inverted and adds the yaw', () => {
  assert.deepEqual(blindSectorsBase({ yaw_deg: 10, inverted: true, blind_sectors: [[100, 140]] }), [[-130, -90]]);
  assert.deepEqual(blindSectorsBase({ yaw_deg: 0, blind_sectors: [[170, -170]] }), [[170, -170]]);
  assert.deepEqual(blindSectorsBase({ yaw_deg: 20, blind_sectors: [[170, 175]] }), [[-170, -165]]);
  assert.deepEqual(blindSectorsBase({ yaw_deg: 0 }), []);
});

test('lidar settings are written as YAML sensors.yaml reads', () => {
  assert.equal(lidarYamlValue([[100, 140], [170, -170]]), '[[100, 140], [170, -170]]');
  assert.equal(lidarYamlValue([]), '[]');
  assert.equal(lidarYamlValue(true), 'true');
  assert.equal(lidarYamlValue('DenseBoost'), 'DenseBoost');
});

// ---------- ignored sensors (enabled: false) ----------
import { lastFrontInUse } from '../www/sensormath.js';

test('coverage ignores ignored sensors', () => {
  assert.equal(coverage([lidar({ enabled: false })]).far, 0);
  assert.ok(coverage([lidar({ enabled: true })]).far > 0.3);
});

test('lastFrontInUse: the last sensor looking ahead', () => {
  const a = { ...tof({ yaw_deg: 0 }), name: 'tof_front' };
  const back = { ...sonar({ yaw_deg: 180 }), name: 'sonar_rear' };
  assert.equal(lastFrontInUse([a, back], 'tof_front'), true);
  assert.equal(lastFrontInUse([a, back, { ...lidar(), name: 'lidar' }], 'tof_front'), false);
  assert.equal(lastFrontInUse([a, { ...tof({ yaw_deg: 30 }), name: 'tof_left' }], 'tof_front'), false);
  assert.equal(lastFrontInUse([a, { ...tof({ yaw_deg: 30, enabled: false }), name: 'tof_left' }], 'tof_front'), true);
  assert.equal(lastFrontInUse([a, back], 'sonar_rear'), false);   // ignoring a rear one: nothing to warn
});

test('lastFrontInUse: a floor sensor does not count as looking ahead', () => {
  const a = { ...tof({ yaw_deg: 0 }), name: 'tof_front' };
  const floor = { ...tof({ yaw_deg: 0, pitch_deg: 40 }), name: 'tof_floor' };
  assert.equal(lastFrontInUse([a, floor], 'tof_front'), true);
});

import { sensorColour } from '../www/sensormath.js';
test("sensorColour: the sensor's own colour, else its type's", () => {
  assert.equal(sensorColour({ type: 'vl53l0x' }), '#a371f7');
  assert.equal(sensorColour({ type: 'vl53l0x', colour: '#FF8800' }), '#ff8800');
  assert.equal(sensorColour({ type: 'hcsr04', colour: 'red' }), '#f0b429');
});

import { PALETTE } from '../www/sensormath.js';
test('PALETTE: 9 different colours, one per Pico connector', () => {
  assert.equal(PALETTE.length, 9);
  assert.equal(new Set(PALETTE).size, 9);
  for (const c of PALETTE) assert.match(c, /^#[0-9a-f]{6}$/);
});
