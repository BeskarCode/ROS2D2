// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { statusPills } from '../www/statuspills.js';

const now = 100000;
const all = { ros: true, mega: true, picoAt: now - 500, pico: { connected: true, firmware: '0.3.0', commit: 'abc' },
  scanAt: now - 300, cams: { cam1: now - 400 }, auto: false, mode: '', track: false };
const byKey = (list) => Object.fromEntries(list.map((p) => [p.key, p]));

test('the same six pills, "Name: state", in order', () => {
  const p = statusPills(all, now);
  assert.deepEqual(p.map((x) => x.key), ['ros', 'mega', 'pico', 'lidar', 'cam', 'mode']);
  const k = byKey(p);
  assert.equal(k.ros.text, 'ROS: connected'); assert.equal(k.ros.cls, 'ok');
  assert.equal(k.mega.text, 'Mega: connected');
  assert.equal(k.pico.text, 'Pico: 0.3.0');               // short: the version only
  assert.equal(k.lidar.text, 'Lidar: scanning');
  assert.equal(k.cam.text, 'Camera: online');
  assert.equal(k.mode.text, 'Mode: off'); assert.equal(k.mode.cls, '');
});

test('things gone go red; nothing known yet is neutral', () => {
  const k = byKey(statusPills({ ...all, ros: false, mega: false, picoAt: now - 5000, scanAt: now - 9000, cams: { cam1: now - 9000 } }, now));
  assert.equal(k.ros.text, 'ROS: not connected'); assert.equal(k.ros.cls, 'bad');
  assert.equal(k.mega.text, 'Mega: not connected'); assert.equal(k.mega.cls, 'bad');
  assert.equal(k.pico.text, 'Pico: not connected'); assert.equal(k.pico.cls, 'bad');
  assert.equal(k.lidar.text, 'Lidar: no scans'); assert.equal(k.lidar.cls, 'warn');
  assert.equal(k.cam.text, 'Camera: offline'); assert.equal(k.cam.cls, 'bad');
  const fresh = byKey(statusPills({ ros: null }, now));
  assert.equal(fresh.ros.text, 'ROS: …'); assert.equal(fresh.cam.text, 'Camera: none');
});

test('two cameras: how many answer', () => {
  const k = byKey(statusPills({ ...all, cams: { cam1: now - 100, cam2: now - 9000 } }, now));
  assert.equal(k.cam.text, 'Cameras: 1 of 2 online'); assert.equal(k.cam.cls, 'warn');
});

test('mode: the automatic one on, or face tracking', () => {
  assert.equal(byKey(statusPills({ ...all, auto: true, mode: 'patrol' }, now)).mode.text, 'Mode: Patrol');
  assert.equal(byKey(statusPills({ ...all, auto: true, mode: 'patrol' }, now)).mode.cls, 'ok');
  assert.equal(byKey(statusPills({ ...all, track: true }, now)).mode.text, 'Mode: face tracking');
});

test('a source never heard after the wait (time 0) reads as gone, not as unknown', () => {
  const k = Object.fromEntries(statusPills({ ...all, picoAt: 0, scanAt: 0 }, now).map((p) => [p.key, p]));
  assert.equal(k.pico.text, 'Pico: not connected');
  assert.equal(k.lidar.text, 'Lidar: no scans');
});

test('each pill takes you to the Setup tab about it', () => {
  const k = Object.fromEntries(statusPills(all, now).map((p) => [p.key, p]));
  assert.equal(k.pico.href, 'setup.html#system');
  assert.equal(k.lidar.href, 'setup.html#sensors');
  assert.equal(k.cam.href, 'setup.html#cameras');
  assert.equal(k.mode.href, 'setup.html#modes');
});
