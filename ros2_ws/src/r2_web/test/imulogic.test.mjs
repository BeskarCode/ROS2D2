// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { BUMP_ALARM, bar, boxMismatch, createChecks, euler, linearAccel, statusPills, tiltClass, tiltOf } from '../www/imulogic.js';

const round = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, Math.round(v) + 0]));
const OK = { connected: true, fps: 100, bad_frames: 0, port: '/dev/ttyAMA3', box: 'standing', front: '+x', in_use: true,
  invert_yaw: false, levelled: true, level: { roll_deg: 0, pitch_deg: 10 }, simulate: false, error: '', bump: 0 };

test('euler: identity is level', () => assert.deepEqual(round(euler({ x: 0, y: 0, z: 0, w: 1 })), { roll: 0, pitch: 0, yaw: 0 }));
test('euler: pitch 10 front down', () => assert.equal(Math.round(euler({ x: 0, y: Math.sin(Math.PI / 36), z: 0, w: Math.cos(Math.PI / 36) }).pitch), 10));
test('euler: yaw 90 left', () => assert.equal(Math.round(euler({ x: 0, y: 0, z: Math.SQRT1_2, w: Math.SQRT1_2 }).yaw), 90));
test('tiltOf: pitch alone', () => assert.equal(Math.round(tiltOf(0, 15)), 15));
test('tiltClass thresholds', () => assert.deepEqual([5, 10.5, 20.5].map(tiltClass), ['ok', 'warn', 'bad']));
test('linearAccel: still is zero', () => assert.ok(linearAccel(0, 0, [0, 0, 9.80665]).every((v) => Math.abs(v) < 1e-9)));
test('linearAccel: tilted still is zero', () => {
  const g = 9.80665, s = Math.sin(Math.PI / 18), c = Math.cos(Math.PI / 18);
  assert.ok(linearAccel(0, 10, [-g * s, 0, g * c]).every((v) => Math.abs(v) < 1e-9));
});
test('bar: centred, clamped', () => { assert.deepEqual(bar(1.5), { left: 50, width: 25 }); assert.deepEqual(bar(-9), { left: 0, width: 50 }); });
test('BUMP_ALARM is 6 m/s²', () => assert.equal(BUMP_ALARM, 6));
test('statusPills: no status means no node', () => assert.deepEqual(statusPills(null, 0), [{ text: 'no IMU node', cls: 'bad' }]));
test('statusPills: old status means no node', () => assert.equal(statusPills(OK, 4000)[0].text, 'no IMU node'));
test('statusPills: not connected', () => assert.deepEqual(statusPills({ ...OK, connected: false }, 100)[0], { text: 'not connected', cls: 'bad' }));
test('statusPills: connected and levelled', () => {
  const p = statusPills(OK, 100);
  assert.deepEqual(p[0], { text: 'BNO085 connected', cls: 'ok' });
  assert.ok(p.some((x) => x.text === 'levelled' && x.cls === 'ok'));
  assert.ok(p.some((x) => x.text === '100 frames/s'));
  assert.ok(p.some((x) => x.text === 'box: standing'));
});
test('statusPills: simulated, not levelled, not in use, bad frames', () => {
  const p = statusPills({ ...OK, simulate: true, levelled: false, level: null, in_use: false, bad_frames: 4 }, 100);
  assert.deepEqual(p[0], { text: 'simulated', cls: 'warn' });
  for (const t of ['not levelled yet', 'not in use', 'checksum errors 4']) assert.ok(p.some((x) => x.text === t && x.cls === 'warn'), t);
});
test('statusPills: file error shown', () => assert.ok(statusPills({ ...OK, error: 'box: sideways' }, 100).some((x) => x.cls === 'bad' && x.text.includes('sideways'))));
test('boxMismatch: upside down but standing', () => assert.notEqual(boxMismatch({ ...OK, box: 'standing', level: { roll_deg: 178, pitch_deg: 1 } }), ''));
test('boxMismatch: lying and upside down is fine', () => assert.equal(boxMismatch({ ...OK, box: 'lying', level: { roll_deg: -177, pitch_deg: 1 } }), ''));
test('boxMismatch: lying but right way up', () => assert.notEqual(boxMismatch({ ...OK, box: 'lying', level: { roll_deg: 3, pitch_deg: 1 } }), ''));
test('boxMismatch: not levelled says nothing', () => assert.equal(boxMismatch({ ...OK, level: null }), ''));

// 1.2 s of frames at 100/s, then R2 tilted 6° forward, then turned
function run(c, from, to, f) { for (let t = from; t < to; t += 0.05) c.feed({ t, fps: 100, ...f(t) }); }
const state = (c, n) => c.steps().find((s) => s.n === n).state;

test('checks: frames, tilt, turn left', () => {
  const c = createChecks();
  run(c, 0, 1.2, () => ({ pitch: 1, yaw: 0 }));
  assert.equal(state(c, 1), 'done'); assert.equal(state(c, 2), 'todo');
  run(c, 1.2, 2, () => ({ pitch: 7, yaw: 0 }));
  assert.equal(state(c, 2), 'done'); assert.equal(state(c, 3), 'todo');
  run(c, 2, 3, () => ({ pitch: 7, yaw: 25 }));
  assert.equal(state(c, 3), 'done');
});
test('checks: turning gives inverted when yaw goes down', () => {
  const c = createChecks();
  run(c, 0, 1.2, () => ({ pitch: 0, yaw: 10 }));
  run(c, 1.2, 2, () => ({ pitch: 6, yaw: 10 }));
  run(c, 2, 3, () => ({ pitch: 6, yaw: -15 }));
  assert.equal(state(c, 3), 'inverted');
});
test('checks: step 4 only by hand', () => {
  const c = createChecks();
  run(c, 0, 1.2, () => ({ pitch: 0, yaw: 0 }));
  run(c, 1.2, 2, () => ({ pitch: 6, yaw: 0 }));
  run(c, 2, 3, () => ({ pitch: 6, yaw: 30 }));
  assert.equal(state(c, 4), 'todo');
  c.mark(4);
  assert.equal(state(c, 4), 'done');
  c.reset();
  assert.ok(c.steps().every((s) => s.state === 'todo'));
});
test('checks: frames must keep coming for a second', () => {
  const c = createChecks();
  c.feed({ t: 0, fps: 100, pitch: 0, yaw: 0 }); c.feed({ t: 0.5, fps: 100, pitch: 0, yaw: 0 }); c.feed({ t: 0.9, fps: 10, pitch: 0, yaw: 0 });
  c.feed({ t: 1.5, fps: 100, pitch: 0, yaw: 0 });
  assert.equal(state(c, 1), 'todo');
});
test('checks: yaw across ±180 counts the short way', () => {
  const c = createChecks();
  run(c, 0, 1.2, () => ({ pitch: 0, yaw: 170 }));
  run(c, 1.2, 2, () => ({ pitch: 6, yaw: 170 }));
  run(c, 2, 3, () => ({ pitch: 6, yaw: -165 }));      // +25° through 180
  assert.equal(state(c, 3), 'done');
});
test('statusPills: simulated says it once (no port pill)', () => {
  const p = statusPills({ ...OK, simulate: true, port: 'simulated' }, 100);
  assert.equal(p.filter((x) => x.text === 'simulated').length, 1);
});
